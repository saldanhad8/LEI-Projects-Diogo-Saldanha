"""
Módulo para redução de dimensionalidade e seleção de features (Otimizado)
"""

import numpy as np
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from sklearn.feature_selection import mutual_info_classif
from sklearn.neighbors import NearestNeighbors
import warnings

warnings.filterwarnings('ignore')

def apply_pca(X, n_components=None, variance_threshold=0.90):
    """
    Aplica PCA ao conjunto de features
    """
    # Normalizar os dados (z-score) - Importante para PCA
    # Nota: Se os dados já vierem normalizados do main, isto é redundante mas seguro
    scaler = StandardScaler()
    X_normalized = scaler.fit_transform(X)
    
    # Aplicar PCA
    if n_components is None:
        # Se passarmos um float (0.90), o sklearn escolhe automaticamente 
        # o nº de componentes para explicar 90% da variância.
        pca = PCA(n_components=variance_threshold)
    else:
        # Se passarmos um int, usa esse número fixo de componentes.
        pca = PCA(n_components=n_components)
    
    # 3. Fit e Transform: Calcula autovetores e projeta os dados no novo espaço
    X_pca = pca.fit_transform(X_normalized)
    
    return {
        'X_transformed': X_pca,
        'explained_variance_ratio': pca.explained_variance_ratio_,
        'n_components': pca.n_components_,
        'scaler': scaler,
        'pca': pca
    }

def fisher_score(X, y):
    """
    Calcula Fisher Score para cada feature (Vetorizado para performance)
    """
    classes = np.unique(y)
    n_features = X.shape[1]
    
    # Calcula a média global de cada feature (coluna)
    mean_feat = np.mean(X, axis=0)
    
    # Inicializa vetores para o numerador (Variância Entre Classes) e denominador (Variância Intra-Classe)
    num = np.zeros(n_features)
    den = np.zeros(n_features)
    
    for c in classes:
        # Seleciona apenas as linhas da classe 'c'
        X_c = X[y == c]
        # Número de amostras na classe
        n_c = X_c.shape[0]
        
        if n_c > 0:
            # Média e Variância das features DENTRO desta classe
            mean_c = np.mean(X_c, axis=0)
            var_c = np.var(X_c, axis=0)
            
            # Acumula no Numerador: Quão longe a média da classe está da média global?
            # (Peso pelo tamanho da classe n_c)
            num += n_c * (mean_c - mean_feat)**2
            # Acumula no Denominador: Quão dispersos são os dados dentro da classe?
            den += n_c * var_c
            
    # Evitar divisão por zero
    fisher = np.where(den == 0, 0, num / den)
    return fisher

def relieff_score(X, y, n_neighbors=10, max_samples=2000):
    """
    Implementa algoritmo ReliefF com Otimização de Subsampling.
    
    Se N > max_samples, usa apenas um subconjunto aleatório para calcular os pesos.
    Isto evita que o algoritmo demore horas em datasets grandes.
    """
    n_samples, n_features = X.shape
    classes = np.unique(y)
    
    # --- OTIMIZAÇÃO: SUBSAMPLING ---
    # OTIMIZAÇÃO: Se tivermos 20.000 linhas, o ReliefF é muito lento.
    # Usamos apenas 2000 amostras aleatórias para calcular os pesos.
    if n_samples > max_samples:
        print(f"      [ReliefF] Subsampling: Usando {max_samples} de {n_samples} amostras para acelerar...")
        # Manter a reprodutibilidade
        np.random.seed(42)
        indices = np.random.choice(n_samples, max_samples, replace=False)
        X_subset = X[indices]
        y_subset = y[indices]
        # Usamos o subset como "Query" e "Reference" para velocidade
        X_ref = X_subset
        y_ref = y_subset
        n_samples_iter = max_samples
    else:
        X_subset = X
        y_subset = y
        X_ref = X
        y_ref = y
        n_samples_iter = n_samples

    # Inicializa pesos das features a zero
    weights = np.zeros(n_features)
    
    # Pré-calcular vizinhos mais próximos para todas as amostras do subset
    # Usamos NearestNeighbors do sklearn que é muito mais rápido (KDTree/BallTree)
    nbrs = NearestNeighbors(n_neighbors=n_neighbors, metric='manhattan', n_jobs=-1)
    nbrs.fit(X_ref)
    
    # Iterar sobre as amostras (subset)
    for i in range(n_samples_iter):
        current_sample = X_subset[i].reshape(1, -1)
        current_label = y_subset[i]
        
        # Encontrar vizinhos (inclui a própria amostra, por isso pedimos k+1)
        # Nota: encontrar vizinhos globalmente, depois filtramos por classe
        # ReliefF original procura k hits (mesma classe) e k misses (classe dif)
        
        # Para simplificar e acelerar a implementação manual do ReliefF em Python:
        # 1. Encontrar Hits: Vizinhos da MESMA classe
        class_mask = (y_ref == current_label)
        X_class = X_ref[class_mask]
        
        if len(X_class) > 1:
            # Encontrar k hits
            nn_hits = NearestNeighbors(n_neighbors=min(n_neighbors, len(X_class)), metric='manhattan')
            nn_hits.fit(X_class)
            dist_hits, idx_hits = nn_hits.kneighbors(current_sample)
            
            # Atualizar pesos (Penalizar features que diferem entre Hits)
            # dist_hits já é a soma das diferenças absolutas (Manhattan), mas precisamos feature a feature
            # Vamos pegar nas amostras reais para calcular a diff por feature
            nearest_hits = X_class[idx_hits[0]]
            # 1. Encontrar "Hits" (vizinhos da MESMA classe)
            # Calcula a diferença média entre a amostra e os seus Hits
            # (Queremos que esta diferença seja PEQUENA)
            hit_diff = np.mean(np.abs(current_sample - nearest_hits), axis=0)
            weights -= hit_diff

        # 2. Encontrar Misses: Vizinhos de CLASSES DIFERENTES
        for c in classes:
            if c == current_label:
                continue
                
            class_mask = (y_ref == c)
            X_class = X_ref[class_mask]
            
            if len(X_class) > 0:
                # Probabilidade da classe (P(C))
                p_c = len(X_class) / len(X_ref)
                
                nn_miss = NearestNeighbors(n_neighbors=min(n_neighbors, len(X_class)), metric='manhattan')
                nn_miss.fit(X_class)
                dist_miss, idx_miss = nn_miss.kneighbors(current_sample)
                
                nearest_misses = X_class[idx_miss[0]]
                # 2. Encontrar "Misses" (vizinhos de OUTRAS classes)
                # Calcula a diferença média entre a amostra e os vizinhos da classe oposta
                # (Queremos que esta diferença seja GRANDE, para distinguir as classes)
                miss_diff = np.mean(np.abs(current_sample - nearest_misses), axis=0)
                
                # Recompensa features que separam bem as classes
                weights += p_c * miss_diff

    return weights

def get_feature_ranking(scores, feature_names=None):
    """
    Retorna ranking de features
    """
    # Ordenar por score descendente
    sorted_indices = np.argsort(scores)[::-1]
    
    ranking = []
    for rank, idx in enumerate(sorted_indices):
        name = feature_names[idx] if feature_names is not None else f"Feat_{idx}"
        ranking.append((idx, scores[idx], name))
    
    return ranking