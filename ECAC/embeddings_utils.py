"""
Módulo para extração de embeddings usando HARNet5
Integração com o fluxo de trabalho do TP1.
"""

import torch
import numpy as np
import torch.nn.functional as F

# É necessário importar estas funções dos outros módulos do projeto
from data_loader import load_participant_data
from feature_extraction import segment_data_sliding_window
from scipy.interpolate import interp1d


# ============================================================================
# 1. Carregamento do Modelo
# ============================================================================
def load_harnet_model():
    """
    Carrega o modelo HARNet5 pré-treinado do repositório, extraindo o feature encoder.
    
    Returns:
    --------
    feature_encoder : torch model
        Encoder de features do modelo, ou None se falhar.
    """
    try:
        # Repositório oficial do modelo HARNet5 (necessita de conexão à internet)
        repo = 'OxWearables/ssl-wearables'
        # class_num=5 é um argumento obrigatório para carregar a versão pré-treinada
        model = torch.hub.load(repo, 'harnet5', class_num=5, pretrained=True)
        model.eval()
        
        # Extrair apenas o feature_extractor (o encoder)
        feature_encoder = model.feature_extractor
        # Mover para CPU para compatibilidade
        feature_encoder.to("cpu")
        feature_encoder.eval()
        
        return feature_encoder
    except Exception as e:
        print(f"ERRO: Não foi possível carregar o modelo HARNet5 (PyTorch). Verifique a instalação e conexão à internet: {e}")
        return None

# ============================================================================
# 2. Resampling
# ============================================================================
def resample_to_30hz(acc_xyz, fs_in_hz, target_duration=5.0):
    """
    Reamostra dados de aceleração (X, Y, Z) para 30Hz usando interpolação.
    Assume-se que o segmento original tem uma duração de 5 segundos.
    
    Parameters:
    ----------
    acc_xyz : numpy array
        Dados de aceleração (N_original, 3).
    fs_in_hz : float
        Frequência de amostragem de entrada (e.g., 50Hz).
    target_duration : float
        Duração alvo do segmento em segundos (5s).
        
    Returns:
    --------
    acc_resampled : numpy array
        Dados reamostrados (150, 3) para 5s a 30Hz.
    """
    fs_target = 30.0
    N_target = int(target_duration * fs_target) # 5s * 30Hz = 150 amostras
    
    t_in = np.arange(acc_xyz.shape[0]) / fs_in_hz
    t_out = np.arange(0, target_duration, 1.0/fs_target)
    
    # Garantir que o array de tempo de saída tem exatamente N_target pontos
    if len(t_out) > N_target:
        t_out = t_out[:N_target]
    elif len(t_out) < N_target:
        # Se for preciso, adicionar o último ponto de tempo para atingir 150
        t_out = np.append(t_out, t_out[-1] + (t_out[-1] - t_out[-2]))
        
    acc_resampled = np.zeros((N_target, 3))

    for col in range(3): # X, Y, Z
        # Interpolação linear para reamostrar
        interp_func = interp1d(t_in, acc_xyz[:, col], kind='linear', fill_value="extrapolate")
        acc_resampled[:, col] = interp_func(t_out)
        
    return acc_resampled


# ============================================================================
# 3. Extração de Embeddings por Segmento
# (Função que faltava no último erro)
# ============================================================================
def extract_embeddings_from_segments(segments_list, feature_encoder, batch_size=32):
    """
    Processa uma lista de segmentos (reamostrados a 30Hz) e extrai embeddings 
    usando o feature_encoder HARNet5.
    
    Parameters:
    ----------
    segments_list : list of numpy arrays
        Lista de segmentos de aceleração (N, 3), onde N = 150 (5s @ 30Hz).
    feature_encoder : torch model
        Modelo HARNet5 carregado.
    batch_size : int
        Tamanho do batch para processamento.
        
    Returns:
    --------
    X_embeddings : numpy array
        Embeddings extraídos (n_segments, embedding_dim).
    """
    if feature_encoder is None or not segments_list:
        return np.array([])
        
    all_embeddings = []
    
    feature_encoder.eval() # Modo de avaliação
    
    # Converter a lista de numpy arrays para um único tensor (B, C, L)
    # C=3 (x,y,z), L=150 (sequência)
    segments_tensor = torch.from_numpy(np.array(segments_list)).float()
    # Ajusta as dimensões para o formato que a rede neural espera (Batch, Channels, Time)
    # De (Batch, Time=150, Channels=3) para (Batch, Channels=3, Time=150)
    segments_tensor = segments_tensor.permute(0, 2, 1) 
    
    num_segments = segments_tensor.shape[0]
    
    with torch.no_grad(): # Desativar o cálculo de gradientes
        # Processa em lotes (batches) para não estourar a memória
        for i in range(0, num_segments, batch_size):
            batch = segments_tensor[i:i + batch_size].to("cpu")
            
            # --- FORWARD PASS ---
            # Passa os dados pela rede neural (extrai as features complexas)
            features = feature_encoder(batch)
            
            # Global Average Pooling:
            # A rede devolve algo como (Batch, 128 features, Time).
            # Nós queremos apenas 1 vetor por segmento. Fazemos a média ao longo do tempo.
            if features.ndim > 2:
                features = F.adaptive_avg_pool1d(features, 1).squeeze(-1)
            
            all_embeddings.append(features.cpu().numpy())
            
    X_embeddings = np.concatenate(all_embeddings, axis=0)
    return X_embeddings


# ============================================================================
# 4. Extração de Embeddings do Dataset Completo
# (Função que faltava no erro anterior)
# ============================================================================
def extract_embeddings_dataset(data_path, feature_encoder, window_size, overlap, sampling_rate, num_participants, activities_to_keep):
    """
    Carrega dados de todos os participantes, segmenta, reamostra e extrai embeddings.
    
    Parameters:
    ----------
    ... (parâmetros conforme descrito anteriormente)
        
    Returns:
    --------
    X_embeddings : numpy array
        Embeddings extraídos (n_segments, embedding_dim).
    y_labels : numpy array
        Labels das atividades.
    participant_ids : numpy array
        ID do participante para cada segmento.
    """
    if feature_encoder is None:
        return np.array([]), np.array([]), np.array([])
        
    all_segments = []
    all_labels = []
    all_participant_ids = []

    print(f"A processar dados de 1 a {num_participants} participantes...")

    for participant_id in range(1, num_participants + 1):
        # 1. Carregar dados
        participant_data = load_participant_data(data_path, participant_id)

        if participant_data.size == 0:
            continue

        # Filtrar atividades antes da segmentação
        participant_data = participant_data[np.isin(participant_data[:, -1], activities_to_keep)]
        
        if participant_data.size == 0:
            continue
            
        # 2. Segmentar
        segments = segment_data_sliding_window(participant_data, 
                                               window_size=window_size,
                                               overlap=overlap,
                                               sampling_rate=sampling_rate)
        
        for segment_data, segment_activity in segments:
            
            # Extrair apenas aceleração (colunas 1, 2, 3)
            # Assumimos o formato de entrada [Device ID, Acc(x,y,z), Gyro(x,y,z), Mag(x,y,z), Timestamp, Activity]
            acc_xyz = segment_data[:, 1:4]
            
            # 3. Resample para 30Hz
            acc_resampled = resample_to_30hz(acc_xyz, sampling_rate)
            
            all_segments.append(acc_resampled)
            all_labels.append(segment_activity)
            all_participant_ids.append(participant_id)
    
    print(f"✓ {len(all_segments)} segmentos válidos encontrados")
    
    # 4. Extrair embeddings (chamando a função corrigida)
    print("\nExtraindo embeddings...")
    X_embeddings = extract_embeddings_from_segments(all_segments, feature_encoder, batch_size=32)
    y_labels = np.array(all_labels)
    participant_ids = np.array(all_participant_ids)
    
    if X_embeddings.size > 0:
        print(f"✓ Embeddings extraídos: shape {X_embeddings.shape}")
        
    return X_embeddings, y_labels, participant_ids