try:
    import torch
    print(f"Torch version: {torch.__version__}")
    from torch.distributed import distributed_c10d
    print("distributed_c10d imported successfully")
except Exception as e:
    print(f"Error: {e}")

try:
    import transformers
    print(f"Transformers version: {transformers.__version__}")
except Exception as e:
    print(f"Error importing transformers: {e}")
