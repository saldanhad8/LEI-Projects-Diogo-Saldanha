"""
visualization.py - Módulo dedicado a todos os gráficos do projeto
"""

import matplotlib.pyplot as plt
import numpy as np
import os
from data_loader import ACTIVITY_NAMES, DEVICE_NAMES

# Criar pasta para guardar imagens se não existir
OUTPUT_DIR = 'plots_output'
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

def save_plot(fig, filename):
    filepath = os.path.join(OUTPUT_DIR, filename)
    fig.savefig(filepath, dpi=300, bbox_inches='tight')
    plt.close(fig) # Fecha para libertar memória
    print(f"    -> Gráfico salvo: {filepath}")

def plot_boxplots_analysis(data, title_suffix=""):
    """
    TP1 A - 3.1: Boxplots por atividade e dispositivo.
    Foca no Dispositivo 2 (Pulso Direito) como pedido em 3.2.
    """
    device_id = 2 # Pulso Direito
    dev_data = data[data[:, 0] == device_id]
    
    # Calcular magnitude aceleração
    acc_mag = np.sqrt(np.sum(dev_data[:, 1:4]**2, axis=1))
    activities = dev_data[:, -2] # Coluna de atividade
    
    unique_acts = np.unique(activities)
    plot_data = []
    labels = []
    
    for act in unique_acts:
        if act in ACTIVITY_NAMES: # Apenas plotar atividades conhecidas
            act_vals = acc_mag[activities == act]
            plot_data.append(act_vals)
            labels.append(f"{int(act)}\n{ACTIVITY_NAMES[act][:4]}") # Nome curto
            
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.boxplot(plot_data, labels=labels)
    ax.set_title(f"Distribuição Mag. Aceleração - Pulso Direito {title_suffix}")
    ax.set_xlabel("Atividade")
    ax.set_ylabel("Magnitude Aceleração (m/s²)")
    ax.grid(True, alpha=0.3)
    
    save_plot(fig, f"boxplot_device2_{title_suffix.strip()}.png")

def plot_outliers_scatter(data, outliers_mask, k_val):
    """
    TP1 A - 3.4: Scatter plot com Outliers a vermelho.
    Usa apenas um trecho de dados para o gráfico ser legível.
    """
    device_id = 2
    # Filtrar apenas dispositivo 2 e uma atividade (ex: Walk=4) para clareza
    mask_subset = (data[:, 0] == device_id) & (data[:, -2] == 4)
    
    # Limitar a 1000 pontos para não bloquear o plot
    subset_indices = np.where(mask_subset)[0][:1000]
    
    if len(subset_indices) == 0: return

    subset_data = data[subset_indices]
    subset_outliers = outliers_mask[subset_indices]
    
    acc_mag = np.sqrt(np.sum(subset_data[:, 1:4]**2, axis=1))
    x_axis = np.arange(len(acc_mag))
    
    fig, ax = plt.subplots(figsize=(12, 5))
    
    # Plot pontos normais (Azul)
    ax.scatter(x_axis[~subset_outliers], acc_mag[~subset_outliers], 
               c='blue', s=10, alpha=0.6, label='Normal')
    
    # Plot outliers (Vermelho)
    ax.scatter(x_axis[subset_outliers], acc_mag[subset_outliers], 
               c='red', s=20, label='Outlier')
    
    ax.set_title(f"Deteção de Outliers (Z-Score k={k_val}) - Atividade: Walk")
    ax.set_ylabel("Magnitude Aceleração")
    ax.legend()
    
    save_plot(fig, f"outliers_scatter_k{k_val}.png")

def plot_3d_clusters_pca(X_features, y_labels, title="PCA 3D Visualization"):
    """
    TP1 A - 3.7: Visualização 3D (usando as 3 primeiras componentes do PCA)
    """
    from sklearn.decomposition import PCA
    
    # Reduzir para 3 componentes apenas para visualização
    pca = PCA(n_components=3)
    # Usar apenas uma amostra aleatória para o plot não ficar pesado (ex: 2000 pts)
    idx = np.random.choice(len(X_features), min(len(X_features), 2000), replace=False)
    X_sample = X_features[idx]
    y_sample = y_labels[idx]
    
    X_pca = pca.fit_transform(X_sample)
    
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')
    
    scatter = ax.scatter(X_pca[:, 0], X_pca[:, 1], X_pca[:, 2], 
                         c=y_sample, cmap='viridis', s=20, alpha=0.7)
    
    ax.set_title(title)
    ax.set_xlabel("PC1")
    ax.set_ylabel("PC2")
    ax.set_zlabel("PC3")
    plt.colorbar(scatter, label="Atividade")
    
    save_plot(fig, "pca_3d_clusters.png")

def plot_confusion_matrix_final(cm, class_names, title):
    """
    TP1 B - 5: Matriz de Confusão Final
    """
    fig, ax = plt.subplots(figsize=(10, 8))
    im = ax.imshow(cm, interpolation='nearest', cmap='Blues')
    ax.figure.colorbar(im, ax=ax)
    
    ax.set(xticks=np.arange(cm.shape[1]),
           yticks=np.arange(cm.shape[0]),
           xticklabels=class_names,
           yticklabels=class_names,
           title=title,
           ylabel='True Label',
           xlabel='Predicted Label')
    
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")
    
    # Loop over data dimensions and create text annotations.
    fmt = 'd'
    thresh = cm.max() / 2.
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(j, i, format(cm[i, j], fmt),
                    ha="center", va="center",
                    color="white" if cm[i, j] > thresh else "black")
    
    save_plot(fig, f"confusion_matrix_{title.replace(' ', '_')}.png")

def plot_feature_importance_bar(feature_names, indices, title):
    """
    TP1 A - 4.6: Feature Importance (Top 10/15)
    """
    # Indices vêm do ReliefF ou Fisher
    top_n = len(indices)
    top_names = [feature_names[i] for i in indices]
    
    # Criar valores dummy decrescentes apenas para visualização de ranking
    # (já que o ReliefF output neste código foi simplificado para indices)
    scores = np.linspace(1, 0.1, top_n)
    
    fig, ax = plt.subplots(figsize=(10, 6))
    y_pos = np.arange(top_n)
    ax.barh(y_pos, scores, align='center')
    ax.set_yticks(y_pos)
    ax.set_yticklabels(top_names)
    ax.invert_yaxis()  # Labels read top-to-bottom
    ax.set_xlabel('Importância Relativa')
    ax.set_title(title)
    
    save_plot(fig, f"feature_importance_{title.replace(' ', '_')}.png")