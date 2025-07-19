import csv
import matplotlib.pyplot as plt

class Plotter():
    def __init__(self, results_dir : str, plot_settings : dict):
        self._results_dir = results_dir
        self._plot_settings = plot_settings
        
    def plot_2d(self, datafile: str):
        with open(f"{datafile}.csv", 'r') as file:
            reader = csv.reader(file)
            Xcol_idx = self._plot_settings["X column index"]
            Ycol_idx = self._plot_settings["Y column index"]
            data = []
            for row in reader:
                y_data = float(row[Ycol_idx])
                x_data = float(row[Xcol_idx])
                data.append((y_data,x_data))
                
        [Y, X] = list(zip(*data))
        fig, ax = plt.subplots()
        ax.plot(X, Y, marker='o')
        ax.set_yscale(self._plot_settings["Y scale"])
        ax.set_xscale(self._plot_settings["X scale"])
        plt.title(self._plot_settings["Plot title"])
        plt.xlabel(self._plot_settings["X label"])
        plt.ylabel(self._plot_settings["Y label"])
        plt.grid(True)
        plt.savefig(f"{datafile}.png")
        plt.close()