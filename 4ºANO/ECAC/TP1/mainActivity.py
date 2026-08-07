"""
EA/ECAC 2025 - Trabalho Prático
Classificação de Atividades Humanas

CÓDIGO COMPLETO - INTEGRADO COM VISUALIZAÇÕES E OTIMIZAÇÕES
"""

import numpy as np
import warnings
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from multiprocessing import Pool, cpu_count
import time

# Ignorar warnings de versões/depreciações para limpar a consola
warnings.filterwarnings('ignore')

# ============================================================================
# Importar Módulos Locais
# ============================================================================

from data_loader import load_participant_data, ACTIVITY_NAMES
from outlier_analysis import zscore_outliers
from feature_extraction import (extract_temporal_spectral_features,
                                 segment_data_sliding_window,
                                 get_feature_names)
from dimensionality_reduction import (apply_pca,
                                       relieff_score,
                                       get_feature_ranking)
from embeddings_utils import (load_harnet_model, extract_embeddings_dataset, 
                              resample_to_30hz, extract_embeddings_from_segments)
from smote import smote_augmentation, visualize_smote 
from knn_classifier import KNNClassifier, evaluate_model
from utils import print_section_header, print_subsection

# Módulo de Visualização
from visualization import (plot_boxplots_analysis, plot_outliers_scatter, 
                          plot_3d_clusters_pca, plot_confusion_matrix_final,
                          plot_feature_importance_bar)

# ============================================================================
# CONFIGURAÇÕES GLOBAIS
# ============================================================================

# ATENÇÃO: Ajuste este caminho para a sua pasta real
DATA_PATH = 'C:/Users/diogo/OneDrive/Desktop/UNI-LEI/4ºANO/ECAC/FORTH_TRACE_DATASET-master/FORTH_TRACE_DATASET-master' 

PARTICIPANTS = list(range(1, 16)) # 15 participantes
SAMPLING_RATE = 50 
WINDOW_SIZE = 5 
OVERLAP = 0.5 
ACTIVITIES_TO_KEEP = list(range(1, 8)) # Atividades 1-7 para Parte B
RANDOM_STATE = 42
K_VALUES = [1, 3, 5, 7, 9] 

# Variável global para guardar o melhor modelo para Deployment
BEST_MODEL_FOR_DEPLOYMENT = None

# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================

def _process_segment_wrapper(args):
    """
    Função auxiliar para o multiprocessing.
    Tem de estar no nível superior do módulo para ser 'picklable'.
    """
    segment, fs = args
    return extract_temporal_spectral_features(segment, fs)

# ============================================================================
# TAREFAS - PARTE A
# ============================================================================

def task_A_1_load_data(data_path, participants):
    print_section_header("PARTE A - TAREFA 1: Carregamento de Dados")
    print(f"Carregando dados para os Participantes: {participants}...")
    
    all_participant_data = []
    for participant_id in participants:
        data = load_participant_data(data_path, participant_id) 
        if data.size > 0:
            # Adicionar coluna de ID do participante para rastreamento futuro
            p_id_col = np.full((data.shape[0], 1), participant_id)
            data_with_id = np.hstack((data, p_id_col))
            all_participant_data.append(data_with_id)
            
    if not all_participant_data:
        print("AVISO: Nenhum dado carregado. Verifique o DATA_PATH.")
        return np.array([])
        
    full_raw_data = np.vstack(all_participant_data)
    print(f"\nTotal de amostras brutas: {len(full_raw_data)}")
    return full_raw_data


def task_A_2_3_outlier_analysis(full_raw_data):
    print_section_header("PARTE A - TAREFAS 2 & 3: Análise e Deteção de Outliers")
    
    # [VISUALIZATION] Boxplots antes da limpeza
    print("  -> Gerando Boxplots (Dados Originais)...")
    plot_boxplots_analysis(full_raw_data, title_suffix="Com Outliers")

    # Preparar dados para Z-score (ignorar ID e Activity para cálculo)
    # Estrutura: [DevID, AccX, AccY, AccZ, ..., Act, ID]
    data_standard = full_raw_data[:, :-1] 
    acc_data = data_standard[:, 1:4]
    
    # 3.1 Deteção (Z-score)
    print_subsection("3.1 Deteção e Remoção de Outliers (Z-score)")
    
    # zscore_outliers retorna matriz booleana (N, 3)
    outliers_mask_matrix = zscore_outliers(acc_data, k=4) 
    # Achatamento: Se qualquer eixo for outlier, a linha é outlier
    outliers_mask = np.any(outliers_mask_matrix, axis=1)
    
    # [VISUALIZATION] Scatter plot dos outliers encontrados
    print("  -> Gerando Scatter Plot de Outliers...")
    plot_outliers_scatter(full_raw_data, outliers_mask, k_val=4)
    
    # Remoção
    clean_raw_data = full_raw_data[~outliers_mask] 
    
    # [VISUALIZATION] Boxplots pós limpeza
    print("  -> Gerando Boxplots (Dados Limpos)...")
    plot_boxplots_analysis(clean_raw_data, title_suffix="Sem Outliers")
        
    print(f"Amostras totais: {full_raw_data.shape[0]}")
    print(f"Outliers removidos: {np.sum(outliers_mask)}")
    print(f"Amostras restantes: {clean_raw_data.shape[0]}")
    
    return clean_raw_data


def task_A_4_feature_extraction_and_reduction(raw_data, participants):
    print_section_header("PARTE A - TAREFA 4: Extração de Features (Paralelizada)")
    
    print("  -> Segmentando dados...")
    all_segments = []
    all_labels = []
    all_groups = []
    
    unique_participants = np.unique(raw_data[:, -1])
    
    # Iterar por participante para garantir integridade temporal dos segmentos
    for p_id in unique_participants:
        p_data = raw_data[raw_data[:, -1] == p_id]
        # Remover coluna ID antes de segmentar
        p_data_standard = p_data[:, :-1]
        
        segments = segment_data_sliding_window(p_data_standard, 
                                               window_size=WINDOW_SIZE, 
                                               overlap=OVERLAP, 
                                               sampling_rate=SAMPLING_RATE)
        
        for seg, label in segments:
            all_segments.append(seg)
            all_labels.append(label)
            all_groups.append(p_id)
            
    total_segments = len(all_segments)
    print(f"  -> Total de segmentos a processar: {total_segments}")
    print(f"  -> Iniciando extração de features em paralelo ({cpu_count()} cores)...")
    
    start_time = time.time()
    
    # Preparar argumentos para o Pool
    tasks = [(seg, SAMPLING_RATE) for seg in all_segments]
    
    # Execução Paralela
    with Pool(processes=cpu_count()) as pool:
        X_features_list = pool.map(_process_segment_wrapper, tasks)

    elapsed = time.time() - start_time
    print(f"  -> Extração concluída em {elapsed:.2f} segundos ({elapsed/total_segments:.4f} s/segmento)")

    # Consolidar dados
    X_features_full = np.vstack(X_features_list)
    y_labels_full = np.array(all_labels)
    groups_full = np.array(all_groups)
    feature_names = get_feature_names()
    
    print(f"  -> Dataset Final: {X_features_full.shape}")
    
    # [VISUALIZATION] PCA 3D Clusters
    print("  -> Gerando Visualização 3D (PCA)...")
    plot_3d_clusters_pca(X_features_full, y_labels_full)
    
    return X_features_full, y_labels_full, groups_full, feature_names


# ============================================================================
# TAREFAS - PARTE B
# ============================================================================

def task_B_1_augmentation_and_embeddings(raw_data_filtered, participants):
    print_section_header("PARTE B - TAREFA 1: Data Augmentation e Embeddings")
    
    # 1.1 Extrair features para dataset filtrado (Atvs 1-7)
    print("Extraindo features para o dataset filtrado...")
    X_feat, y_feat, groups_feat, feature_names = task_A_4_feature_extraction_and_reduction(raw_data_filtered, participants)
    
    # 1.3 SMOTE Visualization
    print_subsection("1.3 SMOTE Visualization")
    target_act = 4
    # Filtrar Participante 3 para demonstração limpa
    p3_mask = groups_feat == 3
    if np.sum(p3_mask) > 0:
        X_p3 = X_feat[p3_mask]
        y_p3 = y_feat[p3_mask]
        
        # Gerar sintéticos
        X_aug, y_aug, syn_idx = smote_augmentation(X_p3, y_p3, target_activity=target_act, n_synthetic=3)
        
        try:
            # O plot é gerado e salvo/mostrado dentro desta função ou manualmente
            fig_smote = visualize_smote(X_p3, y_p3, X_aug, y_aug, syn_idx, target_act, title="SMOTE - Participant 3")
            # Salvar explicitamente usando o helper de visualization se necessário
            fig_smote.savefig("plots_output/smote_visualization.png", dpi=300)
            print("Visualização SMOTE salva em 'plots_output'.")
        except Exception as e:
            print(f"Erro ao visualizar SMOTE: {e}")
    
    # 1.4 Embeddings
    print_subsection("1.4 Extração de Embeddings")
    
    X_emb = np.array([])
    y_emb = np.array([])
    groups_emb = np.array([])
    feature_encoder = None
    
    try:
        feature_encoder = load_harnet_model()
        if feature_encoder:
            X_emb, y_emb, groups_emb = extract_embeddings_dataset(
                DATA_PATH, feature_encoder, WINDOW_SIZE, OVERLAP, SAMPLING_RATE, 
                num_participants=len(participants), 
                activities_to_keep=ACTIVITIES_TO_KEEP
            )
    except Exception as e:
        print(f"AVISO: Falha na extração de embeddings ({e}). \nO pipeline continuará apenas com as features manuais.")
    
    return X_feat, y_feat, groups_feat, X_emb, y_emb, groups_emb, feature_encoder, feature_names


def task_B_2_5_evaluation(X_features, y_features, g_features, X_embeddings, y_embeddings, g_embeddings, feature_names):
    global BEST_MODEL_FOR_DEPLOYMENT
    print_section_header("PARTE B - TAREFAS 2 a 5: Avaliação Comparativa")
    
    DATASETS = {
        'FEATURES': {'X': X_features, 'y': y_features, 'groups': g_features},
        'EMBEDDINGS': {'X': X_embeddings, 'y': y_embeddings, 'groups': g_embeddings}
    }
    
    SCENARIOS = ['All', 'PCA_90', 'ReliefF_15']
    STRATEGIES = ['Within-Subject', 'Between-Subjects']
    
    best_overall_f1 = -1
    
    for dataset_name, data in DATASETS.items():
        if data['X'].size == 0: 
            print(f">> Skipping {dataset_name} (Dataset Vazio ou Indisponível)")
            continue
        
        for strategy in STRATEGIES:
            print(f"\n>> Dataset: {dataset_name} | Estratégia: {strategy}")
            
            X, y, groups = data['X'], data['y'], data['groups']
            
            # --- SPLIT DOS DADOS ---
            if strategy == 'Within-Subject':
                # 60% Train, 20% Val, 20% Test (Misturado)
                X_train_val, X_test, y_train_val, y_test = train_test_split(
                    X, y, test_size=0.2, stratify=y, random_state=RANDOM_STATE
                )
                X_train, X_val, y_train, y_val = train_test_split(
                    X_train_val, y_train_val, test_size=0.25, stratify=y_train_val, random_state=RANDOM_STATE
                )
            else: # Between-Subjects (9 Train, 3 Val, 3 Test)
                unique_subs = np.unique(groups)
                np.random.seed(RANDOM_STATE)
                shuffled_subs = np.random.permutation(unique_subs)
                
                # Definir tamanhos seguros
                n_total = len(unique_subs)
                if n_total < 3:
                     # Fallback para debug com poucos participantes
                    n_train, n_val = 1, 1
                else:
                    n_train = int(n_total * 0.6) if n_total < 15 else 9
                    n_val = int(n_total * 0.2) if n_total < 15 else 3
                
                train_subs = shuffled_subs[:n_train]
                val_subs = shuffled_subs[n_train:n_train+n_val]
                test_subs = shuffled_subs[n_train+n_val:]
                
                X_train = X[np.isin(groups, train_subs)]
                y_train = y[np.isin(groups, train_subs)]
                X_val = X[np.isin(groups, val_subs)]
                y_val = y[np.isin(groups, val_subs)]
                X_test = X[np.isin(groups, test_subs)]
                y_test = y[np.isin(groups, test_subs)]
                
            print(f"   Split Sizes -> Train: {len(X_train)}, Val: {len(X_val)}, Test: {len(X_test)}")
            
            if len(X_train) == 0:
                print("   Aviso: Conjunto de treino vazio. Saltando...")
                continue

            for scenario in SCENARIOS:
                print(f"   -> Processando Cenário: {scenario}")
                
                # 1. Normalização (Fit apenas no Treino)
                scaler = StandardScaler().fit(X_train)
                X_train_sc = scaler.transform(X_train)
                X_val_sc = scaler.transform(X_val)
                X_test_sc = scaler.transform(X_test)
                
                X_train_final, X_val_final, X_test_final = X_train_sc, X_val_sc, X_test_sc
                pca_model = None
                selected_indices = None
                
                # 2. Redução / Seleção
                if scenario == 'PCA_90':
                    res = apply_pca(X_train_sc, variance_threshold=0.90)
                    pca_model = res['pca']
                    X_train_final = res['X_transformed'] 
                    X_val_final = pca_model.transform(X_val_sc)
                    X_test_final = pca_model.transform(X_test_sc)
                    print(f"      PCA Components: {res['n_components']}")
                    
                elif scenario == 'ReliefF_15':
                    # Usa versão otimizada com Subsampling
                    scores = relieff_score(X_train_sc, y_train, n_neighbors=10)
                    ranking = get_feature_ranking(scores)
                    selected_indices = [idx for idx, _, _ in ranking[:15]]
                    
                    X_train_final = X_train_sc[:, selected_indices]
                    X_val_final = X_val_sc[:, selected_indices]
                    X_test_final = X_test_sc[:, selected_indices]
                    
                    # [VISUALIZATION] Feature Importance (apenas para Features)
                    # CORREÇÃO AQUI: Passamos a lista completa de feature_names
                    # A função plot_feature_importance_bar vai usar os selected_indices para filtrar
                    if dataset_name == 'FEATURES':
                        plot_feature_importance_bar(feature_names, selected_indices, 
                                                    f"ReliefF Top 15 - {strategy}")
                
                # 3. Modelação e Avaliação
                metrics = evaluate_model(X_train_final, y_train, X_val_final, y_val, 
                                         X_test_final, y_test, K_VALUES, KNNClassifier)
                
                print(f"      Resultado Teste: Acc={metrics['accuracy']:.3f}, F1={metrics['f1_macro']:.3f}, k={metrics['best_k']}")
                
                # [VISUALIZATION] Matriz de Confusão
                cm_title = f"CM {dataset_name} {strategy[:4]} {scenario}"
                # Nomes das classes presentes no teste
                classes_in_test = np.unique(y_test)
                class_names_plot = [ACTIVITY_NAMES.get(c, str(c)) for c in classes_in_test]
                plot_confusion_matrix_final(metrics['confusion_matrix'], class_names_plot, cm_title)
                
                # 4. Guardar Melhor Modelo Global (para deployment)
                if metrics['f1_macro'] > best_overall_f1:
                    best_overall_f1 = metrics['f1_macro']
                    final_knn = KNNClassifier(k=metrics['best_k'])
                    # Treinar com dados combinados (Train+Val)
                    X_combined = np.vstack((X_train_final, X_val_final))
                    y_combined = np.concatenate((y_train, y_val))
                    final_knn.fit(X_combined, y_combined)
                    
                    BEST_MODEL_FOR_DEPLOYMENT = {
                        'feature_type': dataset_name,
                        'scenario': scenario,
                        'scaler': scaler,
                        'pca_model': pca_model,
                        'selected_indices': selected_indices,
                        'model': final_knn,
                        'best_k': metrics['best_k'],
                        'f1': best_overall_f1
                    }

    if BEST_MODEL_FOR_DEPLOYMENT:
        print(f"\nMelhor F1 Global: {best_overall_f1:.4f} ({BEST_MODEL_FOR_DEPLOYMENT['feature_type']} - {BEST_MODEL_FOR_DEPLOYMENT['scenario']})")
    else:
        print("\nNenhum modelo treinado com sucesso.")


def task_B_6_deployment(feature_encoder):
    print_section_header("PARTE B - TAREFA 6: Deployment")
    
    if BEST_MODEL_FOR_DEPLOYMENT is None:
        print("Erro: Nenhum modelo disponível para deployment.")
        return

    print(f"Modelo Ativo: {BEST_MODEL_FOR_DEPLOYMENT['feature_type']} | Cenário: {BEST_MODEL_FOR_DEPLOYMENT['scenario']}")
    
    # Simulação de um input de Deployment (250 amostras = 5s, 9 colunas de sensores)
    input_simulated = np.random.rand(250, 9) 
    processed_input = None
    
    # 1. Pipeline de Features/Embeddings
    if BEST_MODEL_FOR_DEPLOYMENT['feature_type'] == 'FEATURES':
        # Criar wrapper temporário de 12 colunas para compatibilidade
        temp_full = np.zeros((250, 12))
        temp_full[:, 1:10] = input_simulated 
        features_vec = extract_temporal_spectral_features(temp_full, SAMPLING_RATE)
        processed_input = np.array(features_vec).reshape(1, -1)
        
    elif BEST_MODEL_FOR_DEPLOYMENT['feature_type'] == 'EMBEDDINGS' and feature_encoder:
        acc_data = input_simulated[:, 0:3]
        acc_resampled = resample_to_30hz(acc_data, SAMPLING_RATE)
        processed_input = extract_embeddings_from_segments([acc_resampled], feature_encoder)
    
    # 2. Pipeline de Transformação
    if processed_input is not None:
        if BEST_MODEL_FOR_DEPLOYMENT['scaler']:
            processed_input = BEST_MODEL_FOR_DEPLOYMENT['scaler'].transform(processed_input)
            
        if BEST_MODEL_FOR_DEPLOYMENT['scenario'] == 'PCA_90':
            processed_input = BEST_MODEL_FOR_DEPLOYMENT['pca_model'].transform(processed_input)
        elif BEST_MODEL_FOR_DEPLOYMENT['scenario'] == 'ReliefF_15':
            processed_input = processed_input[:, BEST_MODEL_FOR_DEPLOYMENT['selected_indices']]
        
        # 3. Predição
        prediction = BEST_MODEL_FOR_DEPLOYMENT['model'].predict(processed_input)
        act_name = ACTIVITY_NAMES.get(prediction[0], f"Act {prediction[0]}")
        print(f"✓ Classificação do segmento simulado: {act_name} (Label {prediction[0]})")
    else:
        print("Erro: Falha no processamento do input de deployment.")


# ============================================================================
# EXECUÇÃO PRINCIPAL
# ============================================================================
def main_execution():
    # 1. Carregar Dados (Parte A)
    raw_data = task_A_1_load_data(DATA_PATH, PARTICIPANTS)
    if raw_data.size == 0: return
    
    # 2. Análise de Outliers e Limpeza (Parte A)
    clean_data = task_A_2_3_outlier_analysis(raw_data)
    
    # 3. Filtrar para Atividades da Parte B (1-7)
    # A atividade está na coluna -2 (devido à coluna ID adicionada no fim)
    activities_col = clean_data[:, -2]
    mask_b = np.isin(activities_col, ACTIVITIES_TO_KEEP)
    data_b = clean_data[mask_b]
    
    print(f"Dados filtrados para Parte B (Atvs 1-7): {data_b.shape}")
    
    if data_b.size == 0:
        print("Erro: Sem dados após filtragem de atividades. Verifique labels.")
        return

    # 4. Extração, Augmentation e Embeddings (Parte B)
    # feature_names vem do retorno da extração interna
    X_f, y_f, g_f, X_e, y_e, g_e, encoder, feat_names = task_B_1_augmentation_and_embeddings(data_b, PARTICIPANTS)
    
    # 5. Avaliação Comparativa (Parte B)
    task_B_2_5_evaluation(X_f, y_f, g_f, X_e, y_e, g_e, feat_names)
    
    # 6. Deployment (Parte B)
    task_B_6_deployment(encoder)
    
    print("\nExecução Completa. Verifique a pasta 'plots_output' para os gráficos.")

if __name__ == "__main__":
    main_execution()