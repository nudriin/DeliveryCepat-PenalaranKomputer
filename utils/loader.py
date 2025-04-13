import pickle

def load_graph(path):
    with open(path, "rb") as f:
        return pickle.load(f)