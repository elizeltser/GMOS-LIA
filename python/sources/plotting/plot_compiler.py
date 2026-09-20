class PlotCompiler:
    @staticmethod
    def _smart_fmt(x: float, _pos) -> str:
        if x == 0:
            return "0"
        return f"{float(f'{x:.3g}'):g}"
