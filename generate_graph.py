import networkx as nx
import pickle
from data.generated_graph import node_list, edge_list

# Membuat graf berarah (directed graph)
G = nx.DiGraph()

# Menambahkan node
for node in node_list:
    G.add_node(node["id"], name=node["name"])

# Menambahkan edge
for edge in edge_list:
    G.add_edge(edge["from"], edge["to"], distance=edge["distance"], speed=edge["speed"],
               congestion=edge["congestion"], oneway=edge["oneway"])

# Menyimpan graf menggunakan pickle
with open("data/city_graph.gpickle", "wb") as f:
    pickle.dump(G, f)

print("Graf berhasil disimpan dalam file generated_graph.gpickle")