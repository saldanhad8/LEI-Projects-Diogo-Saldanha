"""
Módulo para Data Augmentation com SMOTE
"""

import numpy as np
from sklearn.neighbors import NearestNeighbors

def smote_augmentation(X, y, target_activity, k_neighbors=5, n_synthetic=1, participant_id=None):
    """
    Implementa o método SMOTE para gerar amostras sintéticas
    
    Parameters:
    -----------
    X : numpy array
        Features do dataset (n_samples, n_features)
    y : numpy array
        Labels das atividades
    target_activity : int
        Atividade alvo para gerar exemplos sintéticos
    k_neighbors : int
        Número de vizinhos a considerar
    n_synthetic : int
        Número de amostras sintéticas a gerar por amostra real
    participant_id : numpy array, optional
        IDs dos participantes (para filtrar)
        
    Returns:
    --------
    X_augmented : numpy array
        Dataset aumentado com amostras sintéticas
    y_augmented : numpy array
        Labels aumentadas
    synthetic_indices : list
        Índices das amostras sintéticas geradas
    """
    
    # Filtrar amostras da atividade alvo
    if participant_id is not None:
        mask = (y == target_activity) & (participant_id == np.unique(participant_id)[0])
    else:
        mask = (y == target_activity)
    
    # Seleciona apenas as amostras da atividade minoritária que queremos aumentar
    X_minority = X[mask]
    
    if len(X_minority) == 0:
        print(f"Aviso: Nenhuma amostra encontrada para atividade {target_activity}")
        return X, y, []
    
    # Ajustar k_neighbors se necessário
    k_actual = min(k_neighbors, len(X_minority) - 1)
    if k_actual < 1:
        print(f"Aviso: Apenas {len(X_minority)} amostras disponíveis. Impossível aplicar SMOTE.")
        return X, y, []
    
    # Prepara k-NN para encontrar vizinhos dentro desta classe
    nbrs = NearestNeighbors(n_neighbors=k_actual + 1)  # +1 porque inclui a própria amostra
    nbrs.fit(X_minority)
    
    # Gerar amostras sintéticas
    synthetic_samples = []
    
    for i in range(len(X_minority)):
        # Encontra os vizinhos da amostra atual
        distances, indices = nbrs.kneighbors([X_minority[i]])
        neighbor_indices = indices[0][1:]  # Excluir o primeiro (própria amostra)
        
        # Gerar n_synthetic amostras
        for _ in range(n_synthetic):
            # Escolher um vizinho aleatoriamente
            nn_idx = np.random.choice(neighbor_indices)
            neighbor = X_minority[nn_idx]
            
            # --- FÓRMULA MÁGICA DO SMOTE ---
            # Cria um ponto algures na linha reta entre a amostra e o vizinho
            # Novo = Atual + (Diferença * fator aleatório entre 0 e 1)
            lambda_val = np.random.random()
            synthetic_sample = X_minority[i] + lambda_val * (neighbor - X_minority[i])
            synthetic_samples.append(synthetic_sample)
    
    # Combinar dados originais com sintéticos
    synthetic_samples = np.array(synthetic_samples)
    X_augmented = np.vstack([X, synthetic_samples])
    y_augmented = np.hstack([y, np.full(len(synthetic_samples), target_activity)])
    
    # Índices das amostras sintéticas
    synthetic_indices = list(range(len(X), len(X_augmented)))
    
    return X_augmented, y_augmented, synthetic_indices


def analyze_class_balance(y, activity_names=None):
    """
    Analisa o balanceamento das classes
    
    Parameters:
    -----------
    y : numpy array
        Labels das atividades
    activity_names : dict, optional
        Mapeamento de IDs para nomes de atividades
        
    Returns:
    --------
    balance_info : dict
        Informação sobre balanceamento
    """
    unique_classes, counts = np.unique(y, return_counts=True)
    total_samples = len(y)
    
    balance_info = {
        'classes': unique_classes,
        'counts': counts,
        'percentages': (counts / total_samples) * 100,
        'total_samples': total_samples,
        'is_balanced': None
    }
    
    # Verificar se está balanceado (diferença máxima < 10%)
    max_percentage = np.max(balance_info['percentages'])
    min_percentage = np.min(balance_info['percentages'])
    balance_info['is_balanced'] = (max_percentage - min_percentage) < 10
    
    print("\n" + "="*70)
    print("ANÁLISE DE BALANCEAMENTO DO DATASET")
    print("="*70)
    print(f"Total de amostras: {total_samples}")
    print(f"\nDistribuição por atividade:")
    print("-"*70)
    
    for cls, count, pct in zip(unique_classes, counts, balance_info['percentages']):
        activity_name = activity_names.get(cls, f"Atividade {int(cls)}") if activity_names else f"Atividade {int(cls)}"
        print(f"{activity_name:30s}: {count:6d} amostras ({pct:5.2f}%)")
    
    print("-"*70)
    if balance_info['is_balanced']:
        print("✓ Dataset BALANCEADO (diferença < 10%)")
    else:
        print("✗ Dataset DESBALANCEADO (diferença ≥ 10%)")
    print("="*70)
    
    return balance_info


def visualize_smote(X_original, y_original, X_augmented, y_augmented, 
                    synthetic_indices, target_activity, title="SMOTE Visualization"):
    """
    Visualiza amostras originais e sintéticas em 2D
    
    Parameters:
    -----------
    X_original : numpy array
        Features originais
    y_original : numpy array
        Labels originais
    X_augmented : numpy array
        Features aumentadas (com sintéticas)
    y_augmented : numpy array
        Labels aumentadas
    synthetic_indices : list
        Índices das amostras sintéticas
    target_activity : int
        Atividade alvo
    title : str
        Título do gráfico
    """
    import matplotlib.pyplot as plt
    
    # Usar apenas as primeiras 2 features para visualização
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Plot todas as atividades originais
    unique_activities = np.unique(y_original)
    colors = plt.cm.tab10(np.linspace(0, 1, len(unique_activities)))
    
    for i, activity in enumerate(unique_activities):
        mask = y_original == activity
        if activity == target_activity:
            ax.scatter(X_original[mask, 0], X_original[mask, 1], 
                      c=[colors[i]], label=f'Atividade {int(activity)} (original)',
                      s=100, alpha=0.6, edgecolors='black', linewidth=1.5)
        else:
            ax.scatter(X_original[mask, 0], X_original[mask, 1], 
                      c=[colors[i]], label=f'Atividade {int(activity)}',
                      s=50, alpha=0.4)
    
    # Plot amostras sintéticas
    X_synthetic = X_augmented[synthetic_indices]
    ax.scatter(X_synthetic[:, 0], X_synthetic[:, 1], 
              c='red', marker='*', s=300, 
              label=f'Atividade {int(target_activity)} (sintética)',
              edgecolors='black', linewidth=2, alpha=0.9)
    
    ax.set_xlabel('Feature 1', fontsize=12)
    ax.set_ylabel('Feature 2', fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.legend(loc='best', fontsize=10)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    return fig