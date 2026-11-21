# demo/repo es el repositorio sobre el que trabaja el agente: su test falla a
# propósito (es el issue benigno que el agente debe arreglar) y corre dentro de
# ese repo con su propio pyproject. pytest desde la raíz no debe recogerlo.
collect_ignore = ["repo"]
