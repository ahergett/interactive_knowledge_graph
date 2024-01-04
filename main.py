import matplotlib.pyplot as plt
import networkx as nx
from openai import OpenAI
import copy
import random
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from tkinter import scrolledtext
import tkinter as tk


class GraphApplication(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Interactive Graph with Chat Interface")
        api_key = 'insert api key'
        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-3.5-turbo"

        self.fig, self.ax = plt.subplots()
        self.G = nx.Graph()
        self.conversation=[]
        self.current_node = 0
        self.G.add_node(self.current_node,
                        label="Start",
                        conversation=[])

        # graph frame
        self.plot_frame = tk.Frame(self, height=800, width=600)  
        self.plot_frame.pack_propagate(0)  
        self.plot_frame.pack(side=tk.LEFT, fill=tk.BOTH)

        # Embed the Matplotlib figure in the Tkinter window
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.plot_frame)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(fill=tk.BOTH, expand=True)
        
        # Connect the Matplotlib click event
        self.canvas.mpl_connect('button_press_event', self.choose_node)
        
        # Create a scrollable text area
        self.text_area = scrolledtext.ScrolledText(self, height=10)
        self.text_area.pack(fill=tk.BOTH, expand=True)

        # Create an input field
        self.input_field = tk.Entry(self)
        self.input_field.pack(fill=tk.X)
        self.input_field.bind("<Return>", self.on_enter)

        self.draw_graph()

    def get_completion(self, messages, model="gpt-3.5-turbo"):
        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0,
            )
        return response.choices[0].message.content

    def get_summary(self, message, model="gpt-3.5-turbo"):
        response = self.client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": "Whats the following message about. You can not use than 3 words, that is very important!"},
                    {"role": "user", "content": message}],
            temperature=0
        )
        return response.choices[0].message.content

    def tree_layout(self, root=0, width=1., vert_gap = 0.1, vert_loc = 0, xcenter = 0.5):
        if not nx.is_tree(self.G):
            raise TypeError('cannot use hierarchy_pos on a graph that is not a tree')

        if root is None:
            if isinstance(self.G, nx.DiGraph):
                root = next(iter(nx.topological_sort(self.G)))  #allows back compatibility with nx version 1.11
            else:
                root = random.choice(list(self.G.nodes))

        def _hierarchy_pos(G, root, width=1., vert_gap = 0.1, vert_loc = 0, xcenter = 0.5, pos = None, parent = None, parsed = []):
            if pos is None:
                pos = {root:(xcenter,vert_loc)}
            else:
                pos[root] = (xcenter, vert_loc)
            children = list(G.neighbors(root))
            if not isinstance(G, nx.DiGraph) and parent is not None:
                children.remove(parent)  
            if len(children)!=0:
                dx = width/len(children) 
                nextx = xcenter - width/2 - dx/2
                for child in children:
                    nextx += dx
                    pos = _hierarchy_pos(G,child, width = dx, vert_gap = vert_gap, 
                        vert_loc = vert_loc-vert_gap, xcenter=nextx, pos=pos, 
                        parent = root, parsed = parsed)
            return pos

        return _hierarchy_pos(self.G, root, width, vert_gap, vert_loc, xcenter)

    def draw_graph(self):
        self.ax.clear()
        pos = self.tree_layout()
        labels = nx.get_node_attributes(self.G, 'label')
        nx.draw(self.G, pos, ax=self.ax, with_labels=True, node_size=0, labels=labels, font_size=3)
        self.canvas.draw()

    def choose_node(self, event):
        nodes = list(self.G.nodes)
        pos = self.tree_layout()
        node_positions = [pos[n] for n in nodes]
        self.input_field.delete(0, tk.END)
        for i, position in enumerate(node_positions):
            dist = ((position[0] - event.xdata) ** 2 + (position[1] - event.ydata) ** 2) ** 0.5
            if dist < 0.1:  # Set a threshold for clicking accuracy
                conversation = copy.deepcopy(self.G.nodes[i].get("conversation"))
                self.update_text_area(self.conversation_to_text(conversation))

                self.conversation = copy.deepcopy(conversation)
                self.current_node = i

    def on_enter(self, event):
        # Handle the input from the user
        input_text = self.input_field.get()
        self.input_field.delete(0, tk.END)
        if not input_text == "":
            self.conversation += [{"role": "user", "content": input_text}]
            response = self.get_completion(self.conversation, self.model)
            self.conversation += [{"role": "system", "content": response}]
            self.update_text_area(self.conversation_to_text(self.conversation))
            j = len(self.G.nodes)
            
            label = self.get_summary(input_text, self.model)
            
            self.G.add_node(j,
                label=label,
                conversation=copy.deepcopy(self.conversation))

            self.G.add_edge(self.current_node, j)
            
            self.current_node = j
            self.draw_graph()


    def conversation_to_text(self, text):
        new_text = ""
        for i in text:
            new_text += f"{i['role']}:\t{i['content']}\n\n\n"
        return new_text
    
    def update_text_area(self, new_text):
        self.text_area.delete(1.0, tk.END)
        self.text_area.insert(tk.END, new_text)
        self.text_area.see(tk.END)


if __name__ == '__main__':
    app = GraphApplication()
    app.mainloop()
