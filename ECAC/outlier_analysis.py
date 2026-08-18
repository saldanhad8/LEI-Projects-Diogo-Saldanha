"""
Módulo para análise e detecção de outliers
"""

import numpy as np
import matplotlib.pyplot as plt
from data_loader import ACTIVITY_NAMES, DEVICE_NAMES
from sklearn.cluster import KMeans

def calculate_magnitude(data, sensor_cols):
    """
    Calcula magnitude de um vetor 3D
    
    Parameters:
    -----------
    data : numpy array
        Dados
    sensor_cols : list
        Índices das colunas x, y, z
        
    Returns:
    --------
    magnitude : numpy array
        Magnitude do vetor
    """
    return np.sqrt(np.sum(data[:, sensor_cols]**2, axis=1))

def plot_boxplots_by_activity(data):
    """
    Gera boxplots dos módulos por atividade e dispositivo
    
    Parameters:
    -----------
    data : numpy array
        Dados completos
    """
    sensors = {
        'Acelerômetro': [1, 2, 3],
        'Giroscópio': [4, 5, 6],
        'Magnetômetro': [7, 8, 9]
    }
    
    devices = np.unique(data[:, 0])
    activities = np.unique(data[:, -1])
    
    for device_id in devices:
        device_data = data[data[:, 0] == device_id]
        device_name = DEVICE_NAMES.get(device_id, f"Device {device_id}")
        
        fig, axes = plt.subplots(1, 3, figsize=(18, 5))
        fig.suptitle(f'Boxplots por Atividade - {device_name}', fontsize=14, fontweight='bold')
        
        for idx, (sensor_name, cols) in enumerate(sensors.items()):
            magnitude = calculate_magnitude(device_data, cols)
            
            # Organizar dados por atividade
            boxplot_data = []
            labels = []
            for activity in activities:
                activity_mask = device_data[:, -1] == activity
                if np.sum(activity_mask) > 0:
                    boxplot_data.append(magnitude[activity_mask])
                    labels.append(int(activity))
            
            axes[idx].boxplot(boxplot_data, labels=labels)
            axes[idx].set_xlabel('Atividade')
            axes[idx].set_ylabel('Magnitude')
            axes[idx].set_title(sensor_name)
            axes[idx].grid(True, alpha=0.3)
            
        plt.tight_layout()
        plt.savefig(f'boxplots_device_{int(device_id)}.png', dpi=300, bbox_inches='tight')
        plt.show()

def calculate_outlier_density_iqr(data, device_id):
    """
    Calcula densidade de outliers usando método IQR
    
    Parameters:
    -----------
    data : numpy array
        Dados completos
    device_id : int
        ID do dispositivo
        
    Returns:
    --------
    densities : dict
        Densidade de outliers por atividade e sensor
    """
    device_data = data[data[:, 0] == device_id]
    activities = np.unique(device_data[:, -1])
    
    sensors = {
        'Acelerômetro': [1, 2, 3],
        'Giroscópio': [4, 5, 6],
        'Magnetômetro': [7, 8, 9]
    }
    
    densities = {}
    
    for activity in activities:
        activity_data = device_data[device_data[:, -1] == activity]
        densities[int(activity)] = {}
        
        for sensor_name, cols in sensors.items():
            magnitude = calculate_magnitude(activity_data, cols)
            
            # Calcula o 1º Quartil (25%) e o 3º Quartil (75%) dos dados
            q1 = np.percentile(magnitude, 25)
            q3 = np.percentile(magnitude, 75)
            # Calcula o Intervalo Interquartil (a altura da "caixa" no boxplot)
            iqr = q3 - q1
            
            # Define os "Bigodes" (Limites aceitáveis)
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            
            # Cria máscara Booleana: é outlier se for menor que o limite inferior OU maior que o superior
            outliers = (magnitude < lower_bound) | (magnitude > upper_bound)
            # Soma os 'True' para saber quantos outliers existem
            n_outliers = np.sum(outliers)
            n_total = len(magnitude)
            
            # Calcula a densidade (percentagem)
            density = (n_outliers / n_total) * 100 if n_total > 0 else 0
            densities[int(activity)][sensor_name] = density
    
    return densities

def zscore_outliers(data, k=3):
    """
    Identifica outliers usando Z-Score
    
    Parameters:
    -----------
    data : numpy array
        Array com os dados
    k : float
        Threshold para Z-Score
        
    Returns:
    --------
    outliers : numpy array (bool)
        Máscara de outliers
    """
    # Calcula a média (μ) de todos os pontos do array
    mean = np.mean(data)
    
    # Calcula o desvio padrão (σ) de todos os pontos
    std = np.std(data)
    
    # Prevenção de erro: se o desvio padrão for 0 (todos os valores iguais), 
    # não é possível dividir por zero, logo não há outliers.
    if std == 0:
        return np.zeros(len(data), dtype=bool)
    
    # Fórmula do Z-Score: |(x - μ) / σ|
    # Calcula a distância de cada ponto à média, em unidades de desvio padrão
    z_scores = np.abs((data - mean) / std)
    
    # Cria uma máscara Booleana (True/False). 
    # True se o Z-score for maior que o limiar k (ex: 3), indicando outlier.
    outliers = z_scores > k
    
    return outliers

def plot_outliers_zscore(data, device_id, k=3):
    """
    Plota outliers identificados com Z-Score
    
    Parameters:
    -----------
    data : numpy array
        Dados completos
    device_id : int
        ID do dispositivo
    k : float
        Threshold Z-Score
    """
    device_data = data[data[:, 0] == device_id]
    activities = np.unique(device_data[:, -1])
    
    sensors = {
        'Acelerômetro': [1, 2, 3],
        'Giroscópio': [4, 5, 6],
        'Magnetômetro': [7, 8, 9]
    }
    
    fig, axes = plt.subplots(len(activities), 3, figsize=(18, len(activities)*3))
    fig.suptitle(f'Outliers Z-Score (k={k}) - {DEVICE_NAMES.get(device_id, "Device")}', 
                 fontsize=14, fontweight='bold')
    
    for act_idx, activity in enumerate(activities):
        activity_data = device_data[device_data[:, -1] == activity]
        
        for sens_idx, (sensor_name, cols) in enumerate(sensors.items()):
            magnitude = calculate_magnitude(activity_data, cols)
            outliers = zscore_outliers(magnitude, k)
            
            ax = axes[act_idx, sens_idx] if len(activities) > 1 else axes[sens_idx]
            
            # Plot pontos normais em azul
            ax.scatter(np.arange(len(magnitude))[~outliers], 
                      magnitude[~outliers], 
                      c='blue', s=1, alpha=0.5, label='Normal')
            
            # Plot outliers em vermelho
            if np.sum(outliers) > 0:
                ax.scatter(np.arange(len(magnitude))[outliers], 
                          magnitude[outliers], 
                          c='red', s=3, alpha=0.8, label='Outlier')
            
            density = (np.sum(outliers) / len(magnitude)) * 100
            
            if act_idx == 0:
                ax.set_title(sensor_name)
            if sens_idx == 0:
                activity_name = ACTIVITY_NAMES.get(activity, f"Act {int(activity)}")
                ax.set_ylabel(f'{activity_name}\nMagnitude')
            
            ax.text(0.02, 0.98, f'Outliers: {density:.1f}%', 
                   transform=ax.transAxes, va='top', fontsize=8,
                   bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
            
            if act_idx == 0 and sens_idx == 2:
                ax.legend(loc='upper right', fontsize=8)
            
            ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(f'zscore_outliers_k{k}_device{device_id}.png', dpi=300, bbox_inches='tight')
    plt.show()

def kmeans_outlier_detection(data, device_id, n_clusters=5, threshold_percentile=95):
    """
    Detecta outliers usando K-Means
    
    Parameters:
    -----------
    data : numpy array
        Dados completos
    device_id : int
        ID do dispositivo
    n_clusters : int
        Número de clusters
    threshold_percentile : float
        Percentil para threshold de distância
        
    Returns:
    --------
    outliers : numpy array (bool)
        Máscara de outliers
    """
    device_data = data[data[:, 0] == device_id]
    
    # Usar magnitudes dos 3 sensores
    acc_mag = calculate_magnitude(device_data, [1, 2, 3])
    gyro_mag = calculate_magnitude(device_data, [4, 5, 6])
    mag_mag = calculate_magnitude(device_data, [7, 8, 9])
    
    # Cria uma matriz X com 3 colunas (Magnitudes de Acc, Gyro, Mag)
    X = np.column_stack([acc_mag, gyro_mag, mag_mag])
    
    # Inicializa e treina o K-Means para encontrar 'n_clusters' centros
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    kmeans.fit(X)
    
    # kmeans.transform(X) devolve a distância de cada ponto a TODOS os centros.
    # np.min(..., axis=1) pega apenas na distância ao centro do cluster MAIS PRÓXIMO (o seu cluster).
    distances = np.min(kmeans.transform(X), axis=1)
    
    # Define o limiar de corte: o valor de distância abaixo do qual estão 95% dos pontos.
    threshold = np.percentile(distances, threshold_percentile)
    # Quem estiver mais longe que esse limiar (os 5% mais distantes) é outlier.
    outliers = distances > threshold
    
    print(f"  K-Means com {n_clusters} clusters:")
    print(f"    Threshold: {threshold:.4f}")
    print(f"    Outliers detectados: {np.sum(outliers)} ({np.sum(outliers)/len(outliers)*100:.2f}%)")
    
    return outliers

def plot_3d_clusters(data, device_id, n_clusters, outliers=None):
    """
    Visualização 3D dos clusters
    
    Parameters:
    -----------
    data : numpy array
        Dados completos
    device_id : int
        ID do dispositivo
    n_clusters : int
        Número de clusters
    outliers : numpy array (bool), optional
        Máscara de outliers
    """
    device_data = data[data[:, 0] == device_id]
    
    # Calcular magnitudes
    acc_mag = calculate_magnitude(device_data, [1, 2, 3])
    gyro_mag = calculate_magnitude(device_data, [4, 5, 6])
    mag_mag = calculate_magnitude(device_data, [7, 8, 9])
    
    X = np.column_stack([acc_mag, gyro_mag, mag_mag])
    
    # K-Means
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X)
    
    # Plot 3D
    fig = plt.figure(figsize=(12, 9))
    ax = fig.add_subplot(111, projection='3d')
    
    # Amostragem para visualização (se dataset muito grande)
    max_points = 5000
    if len(X) > max_points:
        indices = np.random.choice(len(X), max_points, replace=False)
        X_plot = X[indices]
        labels_plot = labels[indices]
        outliers_plot = outliers[indices] if outliers is not None else None
    else:
        X_plot = X
        labels_plot = labels
        outliers_plot = outliers
    
    # Plot clusters
    if outliers_plot is not None:
        # Pontos normais
        ax.scatter(X_plot[~outliers_plot, 0], 
                  X_plot[~outliers_plot, 1], 
                  X_plot[~outliers_plot, 2],
                  c=labels_plot[~outliers_plot], 
                  cmap='viridis', 
                  s=5, alpha=0.6, label='Normal')
        
        # Outliers
        if np.sum(outliers_plot) > 0:
            ax.scatter(X_plot[outliers_plot, 0], 
                      X_plot[outliers_plot, 1], 
                      X_plot[outliers_plot, 2],
                      c='red', s=20, alpha=0.8, marker='x', label='Outlier')
    else:
        ax.scatter(X_plot[:, 0], X_plot[:, 1], X_plot[:, 2],
                  c=labels_plot, cmap='viridis', s=5, alpha=0.6)
    
    # Plot centroides
    centers = kmeans.cluster_centers_
    ax.scatter(centers[:, 0], centers[:, 1], centers[:, 2],
              c='red', s=200, marker='*', edgecolors='black', 
              linewidths=2, label='Centroides')
    
    ax.set_xlabel('Acelerômetro')
    ax.set_ylabel('Giroscópio')
    ax.set_zlabel('Magnetômetro')
    ax.set_title(f'K-Means: {n_clusters} Clusters - {DEVICE_NAMES.get(device_id, "Device")}')
    ax.legend()
    
    plt.tight_layout()
    plt.savefig(f'kmeans_3d_{n_clusters}clusters_device{device_id}.png', 
                dpi=300, bbox_inches='tight')
    plt.show()