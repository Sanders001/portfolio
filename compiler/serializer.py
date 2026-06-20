"""
Utilitários de Serialização de AST.

Foco em JSON-safe (evitando desserialização insegura via Pickle).
BaseSerializer garante conversão segura da AST em dicionários puros.
"""
from abc import ABC, abstractmethod
from typing import Callable, Dict

from .ast_nodes import BaseNode


class BaseSerializer(ABC):
    """Contrato base para serialização de AST para dicionário."""

    @abstractmethod
    def to_dict(self, node: BaseNode) -> dict:
        """Converte uma árvore AST num dicionário recursivo JSON-safe."""
        pass


class BaseDeserializer(ABC):
    """Contrato base para desserialização de dicionário para AST."""

    @abstractmethod
    def from_dict(self, data: dict) -> BaseNode:
        """Converte um dicionário JSON-safe de volta em uma árvore AST."""
        pass


class GenericSerializer(BaseSerializer):
    """
    Serializador genérico.
    Despacha métodos baseado no atributo 'node_type' da instância de BaseNode.
    Exemplo: se node_type for 'identifier', vai chamar `serialize_identifier`.
    """

    def to_dict(self, node: BaseNode) -> dict:
        if node is None:
            return {}

        method_name = f"serialize_{node.node_type}"
        serialize_func = getattr(self, method_name, None)

        if serialize_func is None:
            raise ValueError(f"No serialize handler found for node type: {node.node_type}")

        return serialize_func(node)


class GenericDeserializer(BaseDeserializer):
    """
    Desserializador genérico.
    Usa um registro (factory_map) que mapeia 'node_type' -> Factory Function.
    As DSLs podem registrar suas próprias funções para instanciar as subclasses de BaseNode.
    """

    def __init__(self):
        self._factory_map: Dict[str, Callable[[dict], BaseNode]] = {}

    def register(self, node_type: str, factory: Callable[[dict], BaseNode]) -> None:
        """
        Registra uma factory para um node_type específico.
        Ex: register('identifier', lambda data: IdentifierNode(data['name']))
        """
        self._factory_map[node_type] = factory

    def from_dict(self, data: dict) -> BaseNode:
        if not data:
            raise ValueError("Cannot deserialize empty data.")

        node_type = data.get("type")
        if not node_type:
            raise ValueError("Missing 'type' in AST dictionary representation.")

        factory = self._factory_map.get(node_type)
        if not factory:
            raise ValueError(f"No deserializer factory registered for node type: {node_type}")

        return factory(data)
