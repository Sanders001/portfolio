"""
Registry: Padronização do Chain of Responsibility.

Permite registrar e resolver funções ou handlers (providers) dinamicamente.
"""
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional


class BaseProvider(ABC):
    """
    Contrato para um provider capaz de fornecer Callable/Handlers pelo nome.
    """

    @abstractmethod
    def get(self, name: str, version: Optional[int] = None) -> Optional[Callable]:
        pass


class SimpleCodedProvider(BaseProvider):
    """
    Provider estático, onde os handlers são injetados/registrados manualmente na inicialização.
    """

    def __init__(self):
        self._actions: Dict[str, Callable] = {}

    def register(self, name: str, func: Callable) -> None:
        if name in self._actions:
            raise ValueError(f"Action/Handler already registered: {name}")
        self._actions[name] = func

    def get(self, name: str, version: Optional[int] = None) -> Optional[Callable]:
        return self._actions.get(name)

    def list_all(self) -> Dict[str, Callable]:
        return self._actions.copy()


class BaseRegistry:
    """
    Registry unificado gerenciando múltiplos providers.
    Resolve dependências perguntando aos providers em ordem.
    """

    def __init__(self):
        self.coded_provider = SimpleCodedProvider()
        self.providers: List[BaseProvider] = [self.coded_provider]

    def add_provider(self, provider: BaseProvider) -> None:
        """Adiciona um provider ao chain of responsibility."""
        self.providers.append(provider)

    def register(self, name: str, func: Callable, description: str = "") -> None:
        """Registra manualmente um handler no provider estático default."""
        self.coded_provider.register(name, func)

    def get(self, name: str, version: Optional[int] = None) -> Callable:
        """
        Percorre providers em ordem até encontrar o callable solicitado.
        Levanta ValueError se nenhum provider souber lidar com o request.
        """
        for provider in self.providers:
            func = provider.get(name, version)
            if func:
                return func

        raise ValueError(f"Handler not found in any provider: {name} (version: {version})")

    def exists(self, name: str, version: Optional[int] = None) -> bool:
        """
        Verifica se um handler existe em algum dos providers registrados.
        Ideal para uso em verificações prévias (ex: Semantic Analyzer) sem levantar exceção.
        """
        for provider in self.providers:
            if provider.get(name, version) is not None:
                return True
        return False

    def list_all(self) -> Dict[str, Any]:
        """Lista os handlers registrados estaticamente."""
        return self.coded_provider.list_all()
