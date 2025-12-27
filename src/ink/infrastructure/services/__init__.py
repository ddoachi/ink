"""Infrastructure services module.

This module contains infrastructure implementations of domain service
interfaces. These implementations use specific technologies (files, databases,
external libraries) to fulfill the contracts defined in the domain layer.

Available Implementations:
    PinDirectionServiceImpl: Dictionary-backed pin direction lookup service

Design Pattern:
    The infrastructure layer implements domain interfaces (protocols) defined
    in the domain layer. This follows the Dependency Inversion Principle -
    high-level modules (domain, application) don't depend on low-level modules
    (infrastructure), both depend on abstractions (protocols).

See Also:
    - ink.domain.services: Domain service interfaces
    - docs/architecture/layer-architecture.md: Layer dependencies
"""

from ink.infrastructure.services.pin_direction_service_impl import (
    PinDirectionServiceImpl,
)

__all__ = ["PinDirectionServiceImpl"]
