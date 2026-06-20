"""
Integration Layer — Plugin System with Auto-Discovery.

Implements Hexagonal Architecture (Ports & Adapters) with:
- Interfaces (Ports): Abstract contracts for each integration type
- Registry: In-memory decorator-based adapter registration
- Discovery: Auto-discovery + database synchronization at startup
- Resolver: Per-tenant provider resolution with fallback defaults
"""
