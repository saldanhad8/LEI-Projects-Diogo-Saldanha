"""
Módulo para extração de features temporais e espectrais
"""

import numpy as np
from scipy import stats, signal
from scipy.fft import fft
import warnings
warnings.filterwarnings('ignore')

def segment_data_sliding_window(data, window_size=5, overlap=0.5, sampling_rate=50):
    """
    Segmenta os dados usando janelas deslizantes
    
    Parameters:
    -----------
    data : numpy array
        Dados completos (shape: n_samples, 12)
    window_size : float
        Tamanho da janela em segundos
    overlap : float
        Overlap entre janelas (0-1)
    sampling_rate : int
        Taxa de amostragem em Hz
        
    Returns:
    --------
    segments : list
        Lista de tuplos (segment_data, segment_activity)
    """
    # Calcula quantas amostras correspondem a 5 segundos (5 * 50 = 250 amostras)
    window_samples = int(window_size * sampling_rate)
    
    # Calcula o passo de avanço. Se overlap é 50%, avança 50% da janela (125 amostras)
    step_size = int(window_samples * (1 - overlap))
    
    segments = []
    
    # Verifica se o array de dados é menor que uma única janela. Se for, não há nada para cortar.
    if len(data) < window_samples:
        return segments
    
    # Loop principal: vai de 0 até ao fim, avançando 'step_size' de cada vez
    for start_idx in range(0, len(data) - window_samples + 1, step_size):
        end_idx = start_idx + window_samples
        
        # Extrai o "fatia" (slice) dos dados: da linha start_idx até end_idx
        segment = data[start_idx:end_idx]
        
        # Verifica a coluna da atividade (índice -1, a última coluna)
        # np.unique devolve os valores únicos encontrados nessa coluna
        activities_in_segment = np.unique(segment[:, -1])
        
        # Se len == 1, significa que toda a janela tem a mesma atividade (sem transições)
        if len(activities_in_segment) == 1:
            activity = activities_in_segment[0]
            # Guarda a janela (dados brutos) e a respetiva label
            segments.append((segment, activity))
    
    return segments

def extract_temporal_features(segment_data):
    """
    Extrai features temporais de um segmento
    
    Parameters:
    -----------
    segment_data : numpy array
        Dados do segmento (shape: n_window_samples, 12)
        
    Returns:
    --------
    temporal_features : list
        Lista de features temporais
    """
    features = []
    
    # Para cada sensor (acelerómetro, giroscópio, magnetómetro)
    sensors = {
        'acc': [1, 2, 3],
        'gyro': [4, 5, 6], 
        'mag': [7, 8, 9]
    }
    
    for sensor_name, cols in sensors.items():
        # Dados dos 3 eixos
        x_data = segment_data[:, cols[0]]
        y_data = segment_data[:, cols[1]]
        z_data = segment_data[:, cols[2]]
        
        # Magnitude
        magnitude = np.sqrt(x_data**2 + y_data**2 + z_data**2)
        
        # Features para cada eixo e magnitude
        for axis_name, axis_data in [('x', x_data), ('y', y_data), 
                                   ('z', z_data), ('mag', magnitude)]:
            
            # Estatísticas básicas
            features.append(np.mean(axis_data))           # Média
            features.append(np.std(axis_data))            # Desvio padrão
            features.append(np.median(axis_data))         # Mediana
            features.append(np.min(axis_data))            # Mínimo
            features.append(np.max(axis_data))            # Máximo
            features.append(np.ptp(axis_data))            # Range (max-min)
            
            # Momentos estatísticos
            features.append(stats.skew(axis_data))        # Assimetria
            features.append(stats.kurtosis(axis_data))    # Curtose
            
            # Percentis
            features.append(np.percentile(axis_data, 25)) # Q1
            features.append(np.percentile(axis_data, 50)) # Q2 (mediana)
            features.append(np.percentile(axis_data, 75)) # Q3
            features.append(np.percentile(axis_data, 90)) # P90
            
            # Energia
            features.append(np.sum(axis_data**2))         # Energia
            
            # RMS (Root Mean Square)
            features.append(np.sqrt(np.mean(axis_data**2))) # RMS
            
            # MAD (Mean Absolute Deviation)
            features.append(np.mean(np.abs(axis_data - np.mean(axis_data))))
            
            # IQR (Interquartile Range)
            q75, q25 = np.percentile(axis_data, [75, 25])
            features.append(q75 - q25)
            
            # Zero Crossing Rate
            zero_crossings = np.where(np.diff(np.signbit(axis_data)))[0]
            features.append(len(zero_crossings) / len(axis_data))
            
            # Autocorrelação no lag 1
            if len(axis_data) > 1:
                autocorr = np.correlate(axis_data - np.mean(axis_data), 
                                      axis_data - np.mean(axis_data), mode='full')
                autocorr = autocorr[len(autocorr)//2:]
                if autocorr[0] != 0:
                    features.append(autocorr[1] / autocorr[0])
                else:
                    features.append(0)
            else:
                features.append(0)
    
    return features

def extract_spectral_features(segment_data, sampling_rate=50):
    """
    Extrai features espectrais de um segmento
    
    Parameters:
    -----------
    segment_data : numpy array
        Dados do segmento
    sampling_rate : int
        Taxa de amostragem
        
    Returns:
    --------
    spectral_features : list
        Lista de features espectrais
    """
    features = []
    
    sensors = {
        'acc': [1, 2, 3],
        'gyro': [4, 5, 6],
        'mag': [7, 8, 9]
    }
    
    for sensor_name, cols in sensors.items():
        # Dados dos 3 eixos
        x_data = segment_data[:, cols[0]]
        y_data = segment_data[:, cols[1]]
        z_data = segment_data[:, cols[2]]
        
        # Magnitude
        magnitude = np.sqrt(x_data**2 + y_data**2 + z_data**2)
        
        for axis_name, axis_data in [('x', x_data), ('y', y_data),
                                   ('z', z_data), ('mag', magnitude)]:
            
            # Aplicar FFT
            n = len(axis_data)
            if n > 0:
                # Remover DC component
                signal_clean = axis_data - np.mean(axis_data)
                
                # Aplicar FFT
                fft_vals = np.abs(fft(signal_clean))
                fft_freq = np.fft.fftfreq(n, 1/sampling_rate)
                
                # Manter apenas frequências positivas
                positive_freq = fft_freq > 0
                fft_vals = fft_vals[positive_freq]
                fft_freq = fft_freq[positive_freq]
                
                if len(fft_vals) > 0:
                    # Features espectrais básicas
                    features.append(np.sum(fft_vals))              # Energia espectral total
                    features.append(np.mean(fft_vals))             # Média espectral
                    features.append(np.std(fft_vals))              # Desvio padrão espectral
                    features.append(np.median(fft_vals))           # Mediana espectral
                    
                    # Frequência espectral centroid
                    if np.sum(fft_vals) > 0:
                        spectral_centroid = np.sum(fft_freq * fft_vals) / np.sum(fft_vals)
                    else:
                        spectral_centroid = 0
                    features.append(spectral_centroid)
                    
                    # Largura de banda espectral
                    if spectral_centroid > 0 and np.sum(fft_vals) > 0:
                        bandwidth = np.sqrt(np.sum(((fft_freq - spectral_centroid)**2) * fft_vals) / np.sum(fft_vals))
                    else:
                        bandwidth = 0
                    features.append(bandwidth)
                    
                    # Frequência dominante (pico espectral)
                    dominant_freq = fft_freq[np.argmax(fft_vals)]
                    features.append(dominant_freq)
                    
                    # Magnitude da frequência dominante
                    features.append(np.max(fft_vals))
                    
                    # Entropia espectral
                    spectral_power = fft_vals / np.sum(fft_vals)
                    spectral_entropy = -np.sum(spectral_power * np.log2(spectral_power + 1e-12))
                    features.append(spectral_entropy)
                    
                    # Razão entre bandas de frequência
                    low_band = (fft_freq <= 5)  # 0-5 Hz
                    mid_band = (fft_freq > 5) & (fft_freq <= 10)  # 5-10 Hz
                    high_band = (fft_freq > 10)  # >10 Hz
                    
                    low_power = np.sum(fft_vals[low_band]) if np.any(low_band) else 0
                    mid_power = np.sum(fft_vals[mid_band]) if np.any(mid_band) else 0
                    high_power = np.sum(fft_vals[high_band]) if np.any(high_band) else 0
                    total_power = np.sum(fft_vals)
                    
                    if total_power > 0:
                        features.append(low_power / total_power)
                        features.append(mid_power / total_power)
                        features.append(high_power / total_power)
                    else:
                        features.extend([0, 0, 0])
                else:
                    # Adicionar zeros se não houver dados espectrais
                    features.extend([0] * 12)
            else:
                # Adicionar zeros se não houver dados
                features.extend([0] * 12)
    
    return features

def extract_correlation_features(segment_data):
    """
    Extrai features de correlação entre sensores
    
    Parameters:
    -----------
    segment_data : numpy array
        Dados do segmento
        
    Returns:
    --------
    correlation_features : list
        Lista de features de correlação
    """
    features = []
    
    # Dados dos sensores
    acc_x = segment_data[:, 1]
    acc_y = segment_data[:, 2]
    acc_z = segment_data[:, 3]
    gyro_x = segment_data[:, 4]
    gyro_y = segment_data[:, 5]
    gyro_z = segment_data[:, 6]
    mag_x = segment_data[:, 7]
    mag_y = segment_data[:, 8]
    mag_z = segment_data[:, 9]
    
    # Calcular magnitudes
    acc_mag = np.sqrt(acc_x**2 + acc_y**2 + acc_z**2)
    gyro_mag = np.sqrt(gyro_x**2 + gyro_y**2 + gyro_z**2)
    mag_mag = np.sqrt(mag_x**2 + mag_y**2 + mag_z**2)
    
    # Lista de sinais para correlação
    signals = {
        'acc_x': acc_x, 'acc_y': acc_y, 'acc_z': acc_z, 'acc_mag': acc_mag,
        'gyro_x': gyro_x, 'gyro_y': gyro_y, 'gyro_z': gyro_z, 'gyro_mag': gyro_mag,
        'mag_x': mag_x, 'mag_y': mag_y, 'mag_z': mag_z, 'mag_mag': mag_mag
    }
    
    signal_names = list(signals.keys())
    
    # Correlações entre pares de sensores importantes
    important_pairs = [
        ('acc_x', 'acc_y'), ('acc_x', 'acc_z'), ('acc_y', 'acc_z'),
        ('gyro_x', 'gyro_y'), ('gyro_x', 'gyro_z'), ('gyro_y', 'gyro_z'),
        ('acc_mag', 'gyro_mag'), ('acc_mag', 'mag_mag'), ('gyro_mag', 'mag_mag')
    ]
    
    for sensor1, sensor2 in important_pairs:
        if sensor1 in signals and sensor2 in signals:
            corr = np.corrcoef(signals[sensor1], signals[sensor2])[0, 1]
            if np.isnan(corr):
                corr = 0
            features.append(corr)
        else:
            features.append(0)
    
    return features

def extract_temporal_spectral_features(segment_data, sampling_rate=50):
    """
    Extrai todas as features temporais e espectrais de um segmento
    
    Parameters:
    -----------
    segment_data : numpy array
        Dados do segmento
    sampling_rate : int
        Taxa de amostragem
        
    Returns:
    --------
    all_features : numpy array
        Array com todas as features extraídas
    """
    temporal_features = extract_temporal_features(segment_data)
    spectral_features = extract_spectral_features(segment_data, sampling_rate)
    correlation_features = extract_correlation_features(segment_data)
    
    # Combinar todas as features
    all_features = temporal_features + spectral_features + correlation_features
    
    # Substituir NaN e Inf por 0
    all_features = np.nan_to_num(all_features, nan=0.0, posinf=0.0, neginf=0.0)
    
    return all_features

def get_feature_names():
    """
    Retorna os nomes de todas as features extraídas
    
    Returns:
    --------
    feature_names : list
        Lista com nomes das features
    """
    feature_names = []
    
    sensors = ['acc', 'gyro', 'mag']
    axes = ['x', 'y', 'z', 'mag']
    temporal_stats = ['mean', 'std', 'median', 'min', 'max', 'range', 
                     'skew', 'kurtosis', 'q1', 'q2', 'q3', 'p90',
                     'energy', 'rms', 'mad', 'iqr', 'zcr', 'autocorr_lag1']
    
    spectral_stats = ['spectral_energy', 'spectral_mean', 'spectral_std', 
                     'spectral_median', 'spectral_centroid', 'spectral_bandwidth',
                     'dominant_freq', 'dominant_magnitude', 'spectral_entropy',
                     'low_freq_ratio', 'mid_freq_ratio', 'high_freq_ratio']
    
    # Nomes das features temporais
    for sensor in sensors:
        for axis in axes:
            for stat in temporal_stats:
                feature_names.append(f"{sensor}_{axis}_{stat}")
    
    # Nomes das features espectrais
    for sensor in sensors:
        for axis in axes:
            for stat in spectral_stats:
                feature_names.append(f"{sensor}_{axis}_{stat}")
    
    # Nomes das features de correlação
    correlation_pairs = [
        'acc_x_acc_y', 'acc_x_acc_z', 'acc_y_acc_z',
        'gyro_x_gyro_y', 'gyro_x_gyro_z', 'gyro_y_gyro_z',
        'acc_mag_gyro_mag', 'acc_mag_mag_mag', 'gyro_mag_mag_mag'
    ]
    
    for pair in correlation_pairs:
        feature_names.append(f"corr_{pair}")
    
    return feature_names