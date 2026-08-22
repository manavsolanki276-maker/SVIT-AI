import os

# Configure cache directories for serverless environments
if os.environ.get('VERCEL') or os.environ.get('AWS_LAMBDA_FUNCTION_NAME'):
    os.environ.setdefault('HF_HOME', '/tmp/huggingface')
    os.environ.setdefault('TRANSFORMERS_CACHE', '/tmp/huggingface')
    os.environ.setdefault('TORCH_HOME', '/tmp/torch')

from langchain_huggingface import HuggingFaceEmbeddings

def get_embedding_model(model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
    """
    Returns local HuggingFace Embeddings model.
    """
    print(f"Loading Embedding Model: {model_name}...")
    cache_dir = '/tmp/huggingface' if (os.environ.get('VERCEL') or os.environ.get('AWS_LAMBDA_FUNCTION_NAME')) else None
    embeddings = HuggingFaceEmbeddings(
        model_name=model_name,
        cache_folder=cache_dir,
        model_kwargs={'device': 'cpu'},
        encode_kwargs={'normalize_embeddings': True}
    )
    return embeddings