# SOLID Principles Guide & Enforcement

## Overview

SOLID is an acronym for five object-oriented design principles that promote maintainable, scalable, and robust software architecture. This guide defines each principle and how they are enforced in this project.

## Principles

### 1. Single Responsibility Principle (SRP)

**Definition**: A class or function should have only one reason to change, meaning it should have only one job or responsibility.

**Enforcement Strategy**:
- **Function Length**: Functions exceeding 50 lines are flagged as potential SRP violations
- **Rationale**: Long functions often indicate multiple responsibilities
- **Action**: Refactor into smaller, focused functions

**Example Violation**:
```python
def process_user_order(user_id, order_items):
    # 80 lines of code that:
    # - Validates user
    # - Calculates prices
    # - Applies discounts
    # - Updates inventory
    # - Sends email
    # - Creates invoice
    pass  # Too many responsibilities!
```

**Example Compliance**:
```python
def validate_user(user_id):
    # Single responsibility: validate user
    pass

def calculate_order_total(order_items):
    # Single responsibility: calculate total
    pass

def apply_discounts(order, user):
    # Single responsibility: apply discounts
    pass
```

---

### 2. Open/Closed Principle (OCP)

**Definition**: Software entities should be open for extension but closed for modification.

**Enforcement Strategy**:
- **Manual Review**: Code reviews focus on extensibility through inheritance, composition, or interfaces
- **No Automated Checks**: OCP is primarily a design decision validated through architecture review

**Example Compliance**:
```typescript
// Base class closed for modification
abstract class PaymentProcessor {
    abstract process(amount: number): void;
}

// Extension without modification
class CreditCardProcessor extends PaymentProcessor {
    process(amount: number): void {
        // Credit card specific logic
    }
}
```

---

### 3. Liskov Substitution Principle (LSP)

**Definition**: Objects of a superclass should be replaceable with objects of its subclasses without breaking the application.

**Enforcement Strategy**:
- **Manual Review**: Architecture reviews ensure inheritance hierarchies maintain behavioral contracts
- **No Automated Checks**: LSP is validated through design patterns and code review

**Example Compliance**:
```python
# All shapes must implement area() and can be substituted
class Shape:
    def area(self) -> float:
        raise NotImplementedError

class Rectangle(Shape):
    def area(self) -> float:
        return self.width * self.height

class Circle(Shape):
    def area(self) -> float:
        return math.pi * self.radius ** 2
```

---

### 4. Interface Segregation Principle (ISP)

**Definition**: Clients should not be forced to depend on interfaces they do not use. Many client-specific interfaces are better than one general-purpose interface.

**Enforcement Strategy**:
- **Interface Size**: Interfaces/types with more than 10 methods or properties are flagged
- **Rationale**: Large interfaces force clients to implement unused methods
- **Action**: Split into smaller, focused interfaces

**Example Violation**:
```typescript
interface Animal {
    // 15+ methods for different animal types
    fly(): void;
    swim(): void;
    run(): void;
    climb(): void;
    // ... many more
}
```

**Example Compliance**:
```typescript
interface Flyable {
    fly(): void;
}

interface Swimmable {
    swim(): void;
}

interface Runnable {
    run(): void;
}

// Classes implement only what they need
class Bird implements Flyable, Runnable {
    fly(): void { /* ... */ }
    run(): void { /* ... */ }
}
```

---

### 5. Dependency Inversion Principle (DIP)

**Definition**: High-level modules should not depend on low-level modules. Both should depend on abstractions.

**Enforcement Strategy**:
- **Import Analysis**: Direct imports of concrete implementations are flagged
- **Heuristic**: Imports from `models/`, `services/`, `repositories/` without `interfaces/` or `abstract/` prefix are flagged
- **Action**: Depend on interfaces or abstract classes instead

**Example Violation**:
```python
# High-level module depends on concrete low-level module
from backend.models.user import User
from backend.services.email_service import EmailService

class UserController:
    def __init__(self):
        self.email_service = EmailService()  # Direct dependency
```

**Example Compliance**:
```python
# High-level module depends on abstraction
from backend.interfaces.user import IUser
from backend.interfaces.email_service import IEmailService

class UserController:
    def __init__(self, email_service: IEmailService):  # Dependency injection
        self.email_service = email_service
```

---

## Automated Enforcement

### Pre-commit Hook: `architecture-check`

The `architecture-check` hook validates SOLID principles before commits:

1. **SRP Check**: Scans all code files for functions > 50 lines
2. **ISP Check**: Scans TypeScript/interface files for interfaces/types > 10 methods/properties
3. **DIP Check**: Flags direct imports of concrete implementations

### Configuration

SOLID enforcement is controlled via `feature_flags.yml`:

```yaml
ai_guardrails:
  enforce_solid_principles: true  # Enable/disable SOLID checks
```

### Error Messages

When violations are detected, the hook provides:
- File path and line number
- Specific violation type (SRP, ISP, or DIP)
- Reference to this guide for remediation

---

## Best Practices

### For AI Agents (Cursor)

1. **Before Writing Code**: Consider SOLID principles in design
2. **SRP**: Break large functions into smaller, focused ones
3. **ISP**: Keep interfaces small and focused
4. **DIP**: Depend on abstractions, not concrete implementations
5. **Refactoring**: If a pre-commit hook flags violations, refactor before committing

### For Human Developers

1. **Code Reviews**: Review for SOLID compliance
2. **Refactoring**: Continuously improve code to align with SOLID
3. **Design**: Plan interfaces and abstractions before implementation
4. **Testing**: SOLID code is easier to test (TDD goes hand-in-hand)

---

## Quality Guarantees

With SOLID enforcement in place:
- ✅ **Maintainable Code**: Single responsibility makes changes predictable
- ✅ **Extensible Design**: Open/closed principle enables growth
- ✅ **Testable Code**: Dependency inversion enables easy mocking
- ✅ **Focused Interfaces**: Interface segregation prevents fat interfaces
- ✅ **Robust Architecture**: Liskov substitution ensures correct inheritance

---

## References

- **TDD Guide**: `1_global_standards/TEST_STRATEGY_TDD.md`
- **Architecture Rules**: `5_reference_architectures/LAYER_RULES.yaml`
- **AI Sandbox Rules**: `0_phase0_bootstrap/AI_SANDBOX_RULES.md`

---

## Summary

SOLID principles are **MANDATORY** and will **BLOCK** commits if violated. The architecture check hook enforces:
- **SRP**: Functions must be ≤ 50 lines
- **ISP**: Interfaces must be ≤ 10 methods/properties
- **DIP**: Must depend on abstractions, not concrete implementations

Violations must be fixed before code can be committed.

