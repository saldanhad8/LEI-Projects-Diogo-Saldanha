"""
Módulo com funções auxiliares
"""

import numpy as np
import matplotlib.pyplot as plt

def print_section_header(title, width=70):
    """
    Imprime um cabeçalho formatado para uma secção
    
    Parameters:
    -----------
    title : str
        Título da secção
    width : int
        Largura do cabeçalho
    """
    print("\n" + "="*width)
    print(title.center(width))
    print("="*width)

def print_subsection(title, width=70):
    """
    Imprime um sub-cabeçalho
    
    Parameters:
    -----------
    title : str
        Título da subsecção
    width : int
        Largura
    """
    print("\n" + "-"*width)
    print(title)
    print("-"*width)

def save_results_to_file(results, filename):
    """
    Guarda resultados num ficheiro de texto
    
    Parameters:
    -----------
    results : dict
        Dicionário com resultados
    filename : str
        Nome do ficheiro
    """
    with open(filename, 'w', encoding='utf-8') as f:
        for key, value in results.items():
            f.write(f"{key}:\n")
            f.write(f"{value}\n\n")
    
    print(f"Resultados guardados em: {filename}")

def plot_feature_importance(scores, feature_names, top_n=20, title="Feature Importance"):
    """
    Plota importância das features
    
    Parameters:
    -----------
    scores : numpy array
        Scores das features
    feature_names : list
        Nomes das features
    top_n : int
        Número de top features a mostrar
    title : str
        Título do gráfico
    """
    # Selecionar top N features
    top_indices = np.argsort(scores)[-top_n:]
    
    plt.figure(figsize=(10, max(6, top_n * 0.3)))
    plt.barh(range(top_n), scores[top_indices])
    
    if feature_names is not None and len(feature_names) > 0:
        plt.yticks(range(top_n), [feature_names[i] for i in top_indices])
    else:
        plt.yticks(range(top_n), [f"Feature {i}" for i in top_indices])
    
    plt.xlabel('Score')
    plt.title(title)
    plt.tight_layout()
    plt.grid(True, alpha=0.3, axis='x')
    
    return plt.gcf()

def calculate_classification_metrics(y_true, y_pred):
    """
    Calcula métricas de classificação básicas
    
    Parameters:
    -----------
    y_true : numpy array
        Labels verdadeiras
    y_pred : numpy array
        Labels previstas
        
    Returns:
    --------
    metrics : dict
        Dicionário com métricas
    """
    accuracy = np.mean(y_true == y_pred)
    
    classes = np.unique(y_true)
    
    # Precisão, recall e F1 por classe
    precision_per_class = {}
    recall_per_class = {}
    f1_per_class = {}
    
    for c in classes:
        tp = np.sum((y_true == c) & (y_pred == c))
        fp = np.sum((y_true != c) & (y_pred == c))
        fn = np.sum((y_true == c) & (y_pred != c))
        
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        
        precision_per_class[c] = precision
        recall_per_class[c] = recall
        f1_per_class[c] = f1
    
    # Médias
    macro_precision = np.mean(list(precision_per_class.values()))
    macro_recall = np.mean(list(recall_per_class.values()))
    macro_f1 = np.mean(list(f1_per_class.values()))
    
    return {
        'accuracy': accuracy,
        'precision_per_class': precision_per_class,
        'recall_per_class': recall_per_class,
        'f1_per_class': f1_per_class,
        'macro_precision': macro_precision,
        'macro_recall': macro_recall,
        'macro_f1': macro_f1
    }

def plot_confusion_matrix(y_true, y_pred, class_names=None):
    """
    Plota matriz de confusão
    
    Parameters:
    -----------
    y_true : numpy array
        Labels verdadeiras
    y_pred : numpy array
        Labels previstas
    class_names : list, optional
        Nomes das classes
    """
    classes = np.unique(np.concatenate([y_true, y_pred]))
    n_classes = len(classes)
    
    # Criar matriz de confusão
    cm = np.zeros((n_classes, n_classes), dtype=int)
    
    for true_label, pred_label in zip(y_true, y_pred):
        true_idx = np.where(classes == true_label)[0][0]
        pred_idx = np.where(classes == pred_label)[0][0]
        cm[true_idx, pred_idx] += 1
    
    # Plot
    fig, ax = plt.subplots(figsize=(10, 8))
    im = ax.imshow(cm, interpolation='nearest', cmap='Blues')
    ax.figure.colorbar(im, ax=ax)
    
    # Labels
    if class_names is None:
        class_names = [str(int(c)) for c in classes]
    
    ax.set(xticks=np.arange(n_classes),
           yticks=np.arange(n_classes),
           xticklabels=class_names,
           yticklabels=class_names,
           xlabel='Predicted Label',
           ylabel='True Label',
           title='Confusion Matrix')
    
    # Rotacionar labels
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")
    
    # Adicionar valores
    thresh = cm.max() / 2.
    for i in range(n_classes):
        for j in range(n_classes):
            ax.text(j, i, format(cm[i, j], 'd'),
                   ha="center", va="center",
                   color="white" if cm[i, j] > thresh else "black")
    
    plt.tight_layout()
    return fig

def check_data_quality(data):
    """
    Verifica qualidade dos dados
    
    Parameters:
    -----------
    data : numpy array
        Dados a verificar
        
    Returns:
    --------
    report : dict
        Relatório de qualidade
    """
    report = {
        'shape': data.shape,
        'n_samples': data.shape[0],
        'n_features': data.shape[1] if len(data.shape) > 1 else 1,
        'has_nan': np.any(np.isnan(data)),
        'has_inf': np.any(np.isinf(data)),
        'n_nan': np.sum(np.isnan(data)),
        'n_inf': np.sum(np.isinf(data))
    }
    
    if len(data.shape) > 1:
        report['features_with_nan'] = [i for i in range(data.shape[1]) 
                                       if np.any(np.isnan(data[:, i]))]
        report['features_with_inf'] = [i for i in range(data.shape[1]) 
                                       if np.any(np.isinf(data[:, i]))]
        
        # Estatísticas básicas
        report['min'] = np.nanmin(data, axis=0)
        report['max'] = np.nanmax(data, axis=0)
        report['mean'] = np.nanmean(data, axis=0)
        report['std'] = np.nanstd(data, axis=0)
    
    return report

def print_data_quality_report(report):
    """
    Imprime relatório de qualidade de dados
    
    Parameters:
    -----------
    report : dict
        Relatório gerado por check_data_quality
    """
    print("\nRELATÓRIO DE QUALIDADE DE DADOS")
    print("="*50)
    print(f"Shape: {report['shape']}")
    print(f"Número de amostras: {report['n_samples']}")
    print(f"Número de features: {report['n_features']}")
    print(f"\nValores faltantes (NaN): {report['n_nan']}")
    print(f"Valores infinitos: {report['n_inf']}")
    
    if report['has_nan']:
        print(f"Features com NaN: {report.get('features_with_nan', [])}")
    
    if report['has_inf']:
        print(f"Features com Inf: {report.get('features_with_inf', [])}")
    
    print("="*50)

def create_summary_plots(all_data):
    """
    Cria gráficos de resumo dos dados
    
    Parameters:
    -----------
    all_data : numpy array
        Todos os dados
    """
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    # Distribuição de atividades
    activities, counts = np.unique(all_data[:, -1], return_counts=True)
    axes[0, 0].bar(activities, counts)
    axes[0, 0].set_xlabel('Atividade')
    axes[0, 0].set_ylabel('Número de Amostras')
    axes[0, 0].set_title('Distribuição de Atividades')
    axes[0, 0].grid(True, alpha=0.3)
    
    # Distribuição de dispositivos
    devices, counts_dev = np.unique(all_data[:, 0], return_counts=True)
    axes[0, 1].bar(devices, counts_dev)
    axes[0, 1].set_xlabel('Dispositivo')
    axes[0, 1].set_ylabel('Número de Amostras')
    axes[0, 1].set_title('Distribuição de Dispositivos')
    axes[0, 1].grid(True, alpha=0.3)
    
    # Distribuição de magnitude de aceleração
    acc_mag = np.sqrt(all_data[:, 1]**2 + all_data[:, 2]**2 + all_data[:, 3]**2)
    axes[1, 0].hist(acc_mag, bins=50, edgecolor='black')
    axes[1, 0].set_xlabel('Magnitude Aceleração')
    axes[1, 0].set_ylabel('Frequência')
    axes[1, 0].set_title('Distribuição - Magnitude Aceleração')
    axes[1, 0].grid(True, alpha=0.3)
    
    # Distribuição de magnitude de giroscópio
    gyro_mag = np.sqrt(all_data[:, 4]**2 + all_data[:, 5]**2 + all_data[:, 6]**2)
    axes[1, 1].hist(gyro_mag, bins=50, edgecolor='black')
    axes[1, 1].set_xlabel('Magnitude Giroscópio')
    axes[1, 1].set_ylabel('Frequência')
    axes[1, 1].set_title('Distribuição - Magnitude Giroscópio')
    axes[1, 1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('data_summary.png', dpi=300, bbox_inches='tight')
    plt.show()