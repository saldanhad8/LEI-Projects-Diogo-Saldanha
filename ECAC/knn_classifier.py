"""
Módulo para classificador K-Nearest Neighbors (Otimizado/Vetorizado)
"""

import numpy as np
from collections import Counter
from sklearn.metrics import (confusion_matrix, accuracy_score, f1_score, 
                            classification_report)
import matplotlib.pyplot as plt
from scipy.spatial.distance import cdist
from scipy.stats import mode

class KNNClassifier:
    """
    Implementação otimizada (vetorizada) do K-Nearest Neighbors.
    Usa matrizes para calcular distâncias, evitando loops lentos do Python.
    """
    
    def __init__(self, k=3, metric='euclidean'):
        """
        Parameters:
        -----------
        k : int
            Número de vizinhos a considerar
        metric : str
            Métrica de distância ('euclidean', 'cityblock', etc.)
        """
        self.k = k
        # Mapeamento de nomes de métricas para o scipy/cdist
        if metric == 'manhattan':
            self.metric = 'cityblock'
        else:
            self.metric = metric
            
        self.X_train = None
        self.y_train = None
        
    def fit(self, X_train, y_train):
        """
        Armazena os dados de treino.
        """
        self.X_train = X_train
        self.y_train = y_train
        
    def predict(self, X_test):
        """
        Prediz labels para dados de teste usando cálculo matricial.
        """
        # 1. Calcular todas as distâncias entre Teste e Treino de uma vez
        # Retorna matriz (N_test, N_train)
        # Nota: Se tiver erros de memória com datasets gigantes (>50k), 
        # pode ser necessário fazer em batches, mas para ~20k isto aguenta bem.
        distances = cdist(X_test, self.X_train, metric=self.metric)
        
        # 2. Obter os índices dos k vizinhos mais próximos
        # np.argsort ordena a matriz de distâncias (menor para maior)
        # Pegamos apenas nas primeiras k colunas
        k_neighbor_indices = np.argsort(distances, axis=1)[:, :self.k]
        
        # 3. Obter as labels correspondentes a esses índices
        k_neighbor_labels = self.y_train[k_neighbor_indices]
        
        # 4. Voto maioritário (Moda)
        # scipy.stats.mode retorna a moda ao longo do eixo
        predictions, _ = mode(k_neighbor_labels, axis=1, keepdims=True)
        
        return predictions.flatten()
    
    def score(self, X_test, y_test):
        predictions = self.predict(X_test)
        return accuracy_score(y_test, predictions)


def evaluate_model(X_train, y_train, X_val, y_val, X_test, y_test, k_values, ClassifierClass, random_state=42):
    """
    Realiza o tunning de hiperparâmetros e avaliação final.
    Otimizado para não recalcular distâncias desnecessariamente se possível,
    mas mantendo a lógica simples de retreino.
    """
    
    best_k = k_values[0]
    best_val_score = -1
    
    print(f"    -> A otimizar K (Valores: {k_values})...")
    
    # --- FASE 1: TUNING (Train vs Val) ---
    for k in k_values:
        # Iniciar classificador
        knn = ClassifierClass(k=k)
        knn.fit(X_train, y_train)
        
        # Previsão
        # Não precisamos de print de progresso aqui porque a versão vetorizada é rápida
        y_val_pred = knn.predict(X_val)
        
        # Avaliação
        val_f1 = f1_score(y_val, y_val_pred, average='macro')
        
        print(f"       [k={k}] F1 Validação: {val_f1:.4f}")
        
        if val_f1 > best_val_score:
            best_val_score = val_f1
            best_k = k
            
    print(f"    -> Melhor k encontrado: {best_k} (Score: {best_val_score:.4f})")
    
    # --- FASE 2: AVALIAÇÃO FINAL (Train+Val vs Test) ---
    print(f"    -> Retreinando com k={best_k} (Train+Val) e avaliando no Teste...")
    
    X_train_full = np.vstack((X_train, X_val))
    y_train_full = np.concatenate((y_train, y_val))
    
    final_knn = ClassifierClass(k=best_k)
    final_knn.fit(X_train_full, y_train_full)
    
    y_test_pred = final_knn.predict(X_test)
    
    # Calcular métricas finais
    accuracy = accuracy_score(y_test, y_test_pred)
    f1_macro = f1_score(y_test, y_test_pred, average='macro')
    cm = confusion_matrix(y_test, y_test_pred)
    
    metrics = {
        'best_k': best_k,
        'accuracy': accuracy,
        'f1_macro': f1_macro,
        'confusion_matrix': cm,
        'y_pred': y_test_pred,
        'y_true': y_test
    }
    
    return metrics

def plot_confusion_matrix(cm, class_names=None, title='Confusion Matrix'):
    """
    Plota matriz de confusão
    """
    n_classes = cm.shape[0]
    
    fig, ax = plt.subplots(figsize=(8, 6))
    im = ax.imshow(cm, interpolation='nearest', cmap='Blues')
    ax.figure.colorbar(im, ax=ax)
    
    if class_names is None:
        class_names = [str(i) for i in range(1, n_classes + 1)]
    
    ax.set(xticks=np.arange(n_classes),
           yticks=np.arange(n_classes),
           xticklabels=class_names,
           yticklabels=class_names,
           title=title,
           ylabel='True label',
           xlabel='Predicted label')
    
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")
    
    thresh = cm.max() / 2.
    for i in range(n_classes):
        for j in range(n_classes):
            ax.text(j, i, format(cm[i, j], 'd'),
                    ha="center", va="center",
                    color="white" if cm[i, j] > thresh else "black")
    plt.tight_layout()
    return fig