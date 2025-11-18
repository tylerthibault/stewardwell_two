# 🏗️ Code Architecture & Design Review

**Reviewer:** Dylan (Backend Genius & Multi-Stack Architect)  
**Date:** 2025-11-14  
**Manager:** @tylerthibault  
**Focus:** System Design, Design Patterns, SOLID Principles & Architecture Excellence

---

## Executive Summary
[Assessment of code architecture, design patterns, dependency management, and structural organization]

**Architecture Health Score:** X/10
- **SOLID Principles:** X/10 (Single responsibility, open/closed, interface segregation, dependency inversion)
- **Design Patterns:** X/10 (Appropriate pattern usage, avoiding over-engineering)
- **Dependency Management:** X/10 (Injection, inversion of control, clean interfaces)
- **Error Handling:** X/10 (Consistent strategy, proper exception hierarchy)
- **Code Organization:** X/10 (Layer separation, module structure, cohesion)

**Key Findings:** X Critical | X High | X Medium | X Low

---

## Architecture Environment Assessment

### Technology Stack Architecture
**Detected Patterns:**
- [ ] **Python**: Django (MVT), FastAPI (Clean Architecture), Flask (Microservices)
- [ ] **Node.js**: Express (Layered), NestJS (Modular), Clean Architecture
- [ ] **C#**: ASP.NET Core (Clean Architecture), Domain-Driven Design (DDD)
- [ ] **Design Patterns**: Repository, Factory, Observer, Strategy, Decorator
- [ ] **Architecture Patterns**: MVC, MVP, MVVM, Hexagonal, Onion, Clean

**Dependency Injection Frameworks:**
- [ ] **Python**: dependency-injector, punq, inject
- [ ] **Node.js**: inversify, awilix, typedi
- [ ] **C#**: Built-in DI, Autofac, Ninject

---

## Dylan's Architecture Crime Scene Investigation

### 🔴 **Critical Architecture Crimes**

#### 1. **God Objects and Violation of Single Responsibility**
**Crime:** Massive classes doing everything
```python
# ❌ GUILTY - The God Class Monster
class UserManager:
    def __init__(self):
        self.db = Database()
        self.email_service = EmailService()
        self.auth_service = AuthService()
        self.payment_service = PaymentService()
        self.analytics = Analytics()
    
    def create_user(self, data):
        # Validation logic
        if not data.get('email'):
            raise ValueError("Email required")
        
        # Database operations
        user = self.db.create_user(data)
        
        # Send welcome email
        self.email_service.send_welcome(user.email)
        
        # Create auth token
        token = self.auth_service.generate_token(user.id)
        
        # Setup payment profile
        self.payment_service.create_profile(user.id)
        
        # Track analytics
        self.analytics.track_signup(user.id)
        
        # Generate reports
        self._generate_signup_report(user)
        
        # Update metrics
        self._update_user_metrics()
        
        return user
    
    # 50+ more methods handling everything from validation to billing
```

**Dylan's Fix:**
```python
# ✅ REDEEMED - Single Responsibility with Clean Architecture

# Domain layer - Core business entities
class User:
    def __init__(self, email: str, username: str):
        self._validate_email(email)
        self._validate_username(username)
        self.email = email
        self.username = username
        self.created_at = datetime.utcnow()
    
    def _validate_email(self, email: str):
        if not email or '@' not in email:
            raise InvalidEmailError("Invalid email format")
    
    def change_email(self, new_email: str):
        self._validate_email(new_email)
        old_email = self.email
        self.email = new_email
        return EmailChangedEvent(self.id, old_email, new_email)

# Application layer - Use cases and orchestration
class CreateUserUseCase:
    def __init__(self, 
                 user_repository: UserRepository,
                 email_service: EmailService,
                 event_publisher: EventPublisher):
        self._user_repository = user_repository
        self._email_service = email_service
        self._event_publisher = event_publisher
    
    async def execute(self, command: CreateUserCommand) -> User:
        # Check if user exists
        existing = await self._user_repository.get_by_email(command.email)
        if existing:
            raise UserAlreadyExistsError(command.email)
        
        # Create domain entity
        user = User(command.email, command.username)
        
        # Persist user
        saved_user = await self._user_repository.save(user)
        
        # Publish domain event
        event = UserCreatedEvent(saved_user.id, saved_user.email)
        await self._event_publisher.publish(event)
        
        return saved_user

# Event handlers - Separate concerns
class UserCreatedEventHandler:
    def __init__(self, email_service: EmailService, analytics: Analytics):
        self._email_service = email_service
        self._analytics = analytics
    
    async def handle(self, event: UserCreatedEvent):
        # Each handler has single responsibility
        await self._email_service.send_welcome_email(event.user_id, event.email)
        await self._analytics.track_user_signup(event.user_id)

# Infrastructure layer - External concerns
class SqlAlchemyUserRepository(UserRepository):
    def __init__(self, session: Session):
        self._session = session
    
    async def save(self, user: User) -> User:
        user_entity = UserEntity(
            email=user.email,
            username=user.username,
            created_at=user.created_at
        )
        self._session.add(user_entity)
        await self._session.commit()
        return user
```

#### 2. **Tight Coupling and Dependency Violations**
**Crime:** Direct dependencies creating impossible-to-test code
```javascript
// ❌ GUILTY - Tight coupling nightmare
class OrderService {
    constructor() {
        // Hard-coded dependencies = testing nightmare
        this.database = new PostgreSQLDatabase('prod_connection_string');
        this.emailService = new SendGridEmailService('api_key_123');
        this.paymentGateway = new StripeGateway('stripe_secret');
        this.logger = new FileLogger('/var/log/orders.log');
    }
    
    async createOrder(orderData) {
        // Impossible to test without hitting real services
        const user = await this.database.getUser(orderData.userId);
        const charge = await this.paymentGateway.charge(orderData.amount);
        await this.emailService.sendOrderConfirmation(user.email);
        this.logger.info(`Order created: ${orderData.id}`);
    }
}
```

**Dylan's Fix:**
```javascript
// ✅ REDEEMED - Dependency injection with interfaces

// Define contracts (interfaces)
class IUserRepository {
    async getById(id) { throw new Error('Not implemented'); }
}

class IPaymentGateway {
    async processPayment(amount, method) { throw new Error('Not implemented'); }
}

class IEmailService {
    async sendEmail(to, subject, body) { throw new Error('Not implemented'); }
}

class ILogger {
    info(message) { throw new Error('Not implemented'); }
}

// Service with proper dependency injection
class OrderService {
    constructor(userRepository, paymentGateway, emailService, logger) {
        this._userRepository = userRepository;
        this._paymentGateway = paymentGateway;
        this._emailService = emailService;
        this._logger = logger;
    }
    
    async createOrder(orderData) {
        try {
            // All dependencies are injected and mockable
            const user = await this._userRepository.getById(orderData.userId);
            
            if (!user) {
                throw new UserNotFoundError(orderData.userId);
            }
            
            const payment = await this._paymentGateway.processPayment(
                orderData.amount, 
                orderData.paymentMethod
            );
            
            const order = new Order(orderData, payment.transactionId);
            
            await this._emailService.sendEmail(
                user.email,
                'Order Confirmation',
                this._buildConfirmationEmail(order)
            );
            
            this._logger.info(`Order created successfully: ${order.id}`);
            
            return order;
            
        } catch (error) {
            this._logger.error(`Order creation failed: ${error.message}`);
            throw error;
        }
    }
}

// Dependency injection container
class DIContainer {
    constructor() {
        this._services = new Map();
    }
    
    register(name, factory, singleton = true) {
        this._services.set(name, { factory, singleton, instance: null });
    }
    
    get(name) {
        const service = this._services.get(name);
        if (!service) {
            throw new Error(`Service ${name} not registered`);
        }
        
        if (service.singleton && service.instance) {
            return service.instance;
        }
        
        const instance = service.factory(this);
        
        if (service.singleton) {
            service.instance = instance;
        }
        
        return instance;
    }
}

// Container setup
const container = new DIContainer();

container.register('userRepository', () => new SqlUserRepository());
container.register('paymentGateway', () => new StripeGateway());
container.register('emailService', () => new SendGridEmailService());
container.register('logger', () => new ConsoleLogger());

container.register('orderService', (c) => new OrderService(
    c.get('userRepository'),
    c.get('paymentGateway'),
    c.get('emailService'),
    c.get('logger')
));
```

#### 3. **Missing Error Handling Strategy**
**Crime:** Inconsistent, scattered error handling
```python
# ❌ GUILTY - Error handling chaos
def process_payment(amount, card_info):
    try:
        charge = stripe.Charge.create(amount=amount, source=card_info)
        return charge
    except Exception as e:
        print(f"Payment failed: {e}")  # Lost in logs
        return None  # Caller has no idea what went wrong

def create_order(user_id, items):
    user = get_user(user_id)
    if not user:
        return {"error": "User not found"}  # String error
    
    total = calculate_total(items)
    if total == 0:
        raise ValueError("Invalid total")  # Exception error
    
    payment = process_payment(total, user.card)
    if not payment:
        return False  # Boolean error
    
    # What type of error handling is this?!
```

**Dylan's Fix:**
```python
# ✅ REDEEMED - Consistent error handling strategy

# Define exception hierarchy
class DomainError(Exception):
    """Base class for all domain errors"""
    def __init__(self, message: str, error_code: str = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__

class ValidationError(DomainError):
    """Validation-related errors"""
    pass

class BusinessRuleError(DomainError):
    """Business rule violations"""
    pass

class InfrastructureError(DomainError):
    """External service failures"""
    pass

# Specific errors
class UserNotFoundError(ValidationError):
    def __init__(self, user_id: int):
        super().__init__(f"User with ID {user_id} not found", "USER_NOT_FOUND")
        self.user_id = user_id

class PaymentDeclinedError(BusinessRuleError):
    def __init__(self, reason: str):
        super().__init__(f"Payment declined: {reason}", "PAYMENT_DECLINED")

class PaymentGatewayError(InfrastructureError):
    def __init__(self, gateway_error: str):
        super().__init__(f"Payment gateway error: {gateway_error}", "GATEWAY_ERROR")

# Result pattern for explicit error handling
from dataclasses import dataclass
from typing import Union, Generic, TypeVar

T = TypeVar('T')
E = TypeVar('E')

@dataclass
class Success(Generic[T]):
    value: T

@dataclass
class Failure(Generic[E]):
    error: E

Result = Union[Success[T], Failure[E]]

# Service with proper error handling
class PaymentService:
    def __init__(self, payment_gateway: IPaymentGateway, logger: ILogger):
        self._gateway = payment_gateway
        self._logger = logger
    
    async def process_payment(self, amount: Decimal, card_info: CardInfo) -> Result[Payment, DomainError]:
        try:
            # Validate input
            if amount <= 0:
                return Failure(ValidationError("Amount must be positive"))
            
            if not self._is_valid_card(card_info):
                return Failure(ValidationError("Invalid card information"))
            
            # Process payment
            payment_result = await self._gateway.charge(amount, card_info)
            
            if payment_result.declined:
                return Failure(PaymentDeclinedError(payment_result.decline_reason))
            
            payment = Payment(
                transaction_id=payment_result.transaction_id,
                amount=amount,
                status='completed'
            )
            
            return Success(payment)
            
        except PaymentGatewayException as e:
            self._logger.error(f"Payment gateway error: {e}")
            return Failure(PaymentGatewayError(str(e)))
        except Exception as e:
            self._logger.error(f"Unexpected payment error: {e}")
            return Failure(InfrastructureError("Payment processing failed"))

# Usage with explicit error handling
class OrderService:
    async def create_order(self, command: CreateOrderCommand) -> Result[Order, DomainError]:
        # Get user
        user_result = await self._user_repository.get_by_id(command.user_id)
        if isinstance(user_result, Failure):
            return user_result
        
        user = user_result.value
        
        # Process payment
        payment_result = await self._payment_service.process_payment(
            command.total_amount, 
            command.card_info
        )
        if isinstance(payment_result, Failure):
            return payment_result
        
        payment = payment_result.value
        
        # Create order
        order = Order(user_id=user.id, payment_id=payment.id, items=command.items)
        
        save_result = await self._order_repository.save(order)
        return save_result
```

### 🟠 **High Priority Issues**

#### 4. **Anemic Domain Model**
**Crime:** Domain objects with no behavior, just data
```csharp
// ❌ GUILTY - Anemic domain objects
public class Order
{
    public int Id { get; set; }
    public int UserId { get; set; }
    public decimal Total { get; set; }
    public string Status { get; set; }
    public DateTime CreatedAt { get; set; }
    // Just getters/setters, no behavior!
}

// All business logic in services
public class OrderService
{
    public void ProcessOrder(Order order)
    {
        // Business logic scattered in service layer
        if (order.Total < 0)
            throw new InvalidOperationException("Invalid total");
        
        if (order.Status == "cancelled")
            throw new InvalidOperationException("Cannot process cancelled order");
        
        order.Status = "processing";
        
        // Calculate discount logic
        if (order.Total > 100)
            order.Total *= 0.9m;
        
        // Shipping calculation
        var shippingCost = order.Total > 50 ? 0 : 9.99m;
        order.Total += shippingCost;
    }
}
```

**Dylan's Fix:**
```csharp
// ✅ REDEEMED - Rich domain model with behavior

public class Order
{
    private readonly List<OrderItem> _items;
    private readonly List<DomainEvent> _events;
    
    // Private constructor enforces valid creation
    private Order(int userId, IReadOnlyList<OrderItem> items)
    {
        Id = 0; // Set by repository
        UserId = userId;
        _items = items.ToList();
        Status = OrderStatus.Pending;
        CreatedAt = DateTime.UtcNow;
        _events = new List<DomainEvent>();
        
        // Domain invariant
        if (!items.Any())
            throw new DomainException("Order must have at least one item");
        
        AddEvent(new OrderCreatedEvent(this));
    }
    
    // Factory method with validation
    public static Order Create(int userId, IReadOnlyList<OrderItem> items)
    {
        if (userId <= 0)
            throw new DomainException("Invalid user ID");
        
        return new Order(userId, items);
    }
    
    // Domain behavior encapsulated
    public void Process(IPricingService pricingService)
    {
        if (Status != OrderStatus.Pending)
            throw new DomainException($"Cannot process order in {Status} status");
        
        // Apply business rules
        var pricing = pricingService.Calculate(this);
        _subtotal = pricing.Subtotal;
        _discount = pricing.Discount;
        _shippingCost = pricing.ShippingCost;
        
        Status = OrderStatus.Processing;
        ProcessedAt = DateTime.UtcNow;
        
        AddEvent(new OrderProcessedEvent(Id, GetTotal()));
    }
    
    public void Cancel(string reason)
    {
        if (Status == OrderStatus.Shipped)
            throw new DomainException("Cannot cancel shipped order");
        
        Status = OrderStatus.Cancelled;
        CancellationReason = reason;
        CancelledAt = DateTime.UtcNow;
        
        AddEvent(new OrderCancelledEvent(Id, reason));
    }
    
    // Business logic encapsulated
    public decimal GetTotal() => _subtotal - _discount + _shippingCost;
    
    public bool IsEligibleForFreeShipping() => _subtotal >= 50m;
    
    public void AddItem(Product product, int quantity)
    {
        if (Status != OrderStatus.Pending)
            throw new DomainException("Cannot modify processed order");
        
        var existingItem = _items.FirstOrDefault(i => i.ProductId == product.Id);
        if (existingItem != null)
        {
            existingItem.UpdateQuantity(existingItem.Quantity + quantity);
        }
        else
        {
            _items.Add(OrderItem.Create(product, quantity));
        }
        
        AddEvent(new OrderItemAddedEvent(Id, product.Id, quantity));
    }
    
    // Encapsulate domain events
    public IReadOnlyList<DomainEvent> GetEvents() => _events.AsReadOnly();
    
    public void ClearEvents() => _events.Clear();
    
    private void AddEvent(DomainEvent domainEvent) => _events.Add(domainEvent);
}

// Value object for order items
public class OrderItem
{
    public int ProductId { get; private set; }
    public string ProductName { get; private set; }
    public decimal UnitPrice { get; private set; }
    public int Quantity { get; private set; }
    
    private OrderItem(int productId, string productName, decimal unitPrice, int quantity)
    {
        ProductId = productId;
        ProductName = productName;
        UnitPrice = unitPrice;
        Quantity = quantity;
    }
    
    public static OrderItem Create(Product product, int quantity)
    {
        if (quantity <= 0)
            throw new DomainException("Quantity must be positive");
        
        if (product.Price < 0)
            throw new DomainException("Product price cannot be negative");
        
        return new OrderItem(product.Id, product.Name, product.Price, quantity);
    }
    
    public void UpdateQuantity(int newQuantity)
    {
        if (newQuantity <= 0)
            throw new DomainException("Quantity must be positive");
        
        Quantity = newQuantity;
    }
    
    public decimal GetLineTotal() => UnitPrice * Quantity;
}
```

#### 5. **Poor Abstraction Layers**
**Crime:** Business logic mixed with infrastructure concerns
```python
# ❌ GUILTY - Mixed concerns and poor layering
def get_user_orders(user_id):
    # Database connection in business logic
    conn = psycopg2.connect("postgresql://...")
    cursor = conn.cursor()
    
    try:
        # Raw SQL mixed with business logic
        cursor.execute("""
            SELECT o.id, o.total, o.status, o.created_at
            FROM orders o
            WHERE o.user_id = %s AND o.status != 'deleted'
        """, (user_id,))
        
        rows = cursor.fetchall()
        
        orders = []
        for row in rows:
            order = {
                'id': row[0],
                'total': row[1],
                'status': row[2],
                'created_at': row[3]
            }
            
            # Business logic mixed with data access
            if order['total'] > 100:
                order['vip_order'] = True
                
            # External service call in data layer
            shipping_info = requests.get(f"https://shipping.api/orders/{order['id']}")
            order['shipping'] = shipping_info.json()
            
            orders.append(order)
        
        return orders
        
    finally:
        conn.close()
```

**Dylan's Fix:**
```python
# ✅ REDEEMED - Clean architecture with proper layering

# Domain Layer - Pure business logic
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime
from typing import List, Optional

@dataclass
class Order:
    id: int
    user_id: int
    total: Decimal
    status: str
    created_at: datetime
    
    def is_vip_order(self) -> bool:
        """Business rule: orders over $100 are VIP"""
        return self.total > Decimal('100.00')
    
    def can_be_cancelled(self) -> bool:
        """Business rule: only pending/processing orders can be cancelled"""
        return self.status in ['pending', 'processing']

# Application Layer - Use cases and orchestration
class IOrderRepository(ABC):
    @abstractmethod
    async def get_by_user_id(self, user_id: int) -> List[Order]:
        pass

class IShippingService(ABC):
    @abstractmethod
    async def get_shipping_info(self, order_id: int) -> dict:
        pass

class GetUserOrdersUseCase:
    def __init__(self, 
                 order_repository: IOrderRepository,
                 shipping_service: IShippingService):
        self._order_repository = order_repository
        self._shipping_service = shipping_service
    
    async def execute(self, user_id: int) -> List[dict]:
        # Get orders from repository
        orders = await self._order_repository.get_by_user_id(user_id)
        
        # Apply business logic
        enriched_orders = []
        for order in orders:
            order_dict = {
                'id': order.id,
                'total': order.total,
                'status': order.status,
                'created_at': order.created_at,
                'vip_order': order.is_vip_order(),
                'can_cancel': order.can_be_cancelled()
            }
            
            # Get additional data if needed
            if order.status in ['shipped', 'delivered']:
                shipping_info = await self._shipping_service.get_shipping_info(order.id)
                order_dict['shipping'] = shipping_info
            
            enriched_orders.append(order_dict)
        
        return enriched_orders

# Infrastructure Layer - External concerns
class SqlOrderRepository(IOrderRepository):
    def __init__(self, session_factory):
        self._session_factory = session_factory
    
    async def get_by_user_id(self, user_id: int) -> List[Order]:
        async with self._session_factory() as session:
            query = """
                SELECT id, user_id, total, status, created_at
                FROM orders
                WHERE user_id = :user_id AND status != 'deleted'
                ORDER BY created_at DESC
            """
            
            result = await session.execute(query, {'user_id': user_id})
            rows = result.fetchall()
            
            return [
                Order(
                    id=row.id,
                    user_id=row.user_id,
                    total=Decimal(str(row.total)),
                    status=row.status,
                    created_at=row.created_at
                )
                for row in rows
            ]

class HttpShippingService(IShippingService):
    def __init__(self, http_client, base_url: str):
        self._http_client = http_client
        self._base_url = base_url
    
    async def get_shipping_info(self, order_id: int) -> dict:
        try:
            response = await self._http_client.get(f"{self._base_url}/orders/{order_id}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            # Log error but don't break the flow
            logger.warning(f"Failed to get shipping info for order {order_id}: {e}")
            return {'status': 'unknown', 'tracking_number': None}

# Presentation Layer - API controllers
from fastapi import APIRouter, Depends

router = APIRouter()

@router.get("/users/{user_id}/orders")
async def get_user_orders(
    user_id: int,
    use_case: GetUserOrdersUseCase = Depends(get_orders_use_case)
):
    orders = await use_case.execute(user_id)
    return {"orders": orders}
```

---

## Multi-Stack Architecture Patterns

### Python (Clean Architecture with FastAPI)
```python
# Project structure following Clean Architecture
"""
src/
├── domain/
│   ├── entities/
│   │   ├── user.py
│   │   └── order.py
│   ├── value_objects/
│   │   ├── email.py
│   │   └── money.py
│   └── repositories/
│       ├── user_repository.py
│       └── order_repository.py
├── application/
│   ├── use_cases/
│   │   ├── create_user.py
│   │   └── process_order.py
│   ├── services/
│   │   └── email_service.py
│   └── dto/
│       ├── user_dto.py
│       └── order_dto.py
├── infrastructure/
│   ├── persistence/
│   │   ├── sql_user_repository.py
│   │   └── sql_order_repository.py
│   ├── external/
│   │   ├── smtp_email_service.py
│   │   └── stripe_payment_service.py
│   └── web/
│       ├── controllers/
│       │   ├── user_controller.py
│       │   └── order_controller.py
│       └── middleware/
│           └── error_handler.py
└── main.py
"""

# Domain entity with rich behavior
class User:
    def __init__(self, user_id: UserId, email: Email, username: str):
        self._id = user_id
        self._email = email
        self._username = self._validate_username(username)
        self._created_at = datetime.utcnow()
        self._domain_events = []
    
    @property
    def id(self) -> UserId:
        return self._id
    
    @property
    def email(self) -> Email:
        return self._email
    
    def change_email(self, new_email: Email) -> None:
        if self._email == new_email:
            return
        
        old_email = self._email
        self._email = new_email
        
        self._add_domain_event(
            UserEmailChangedEvent(self._id, old_email, new_email)
        )
    
    def _validate_username(self, username: str) -> str:
        if not username or len(username.strip()) < 3:
            raise DomainException("Username must be at least 3 characters")
        return username.strip()
    
    def _add_domain_event(self, event: DomainEvent) -> None:
        self._domain_events.append(event)
    
    def get_domain_events(self) -> List[DomainEvent]:
        return self._domain_events.copy()
    
    def clear_domain_events(self) -> None:
        self._domain_events.clear()

# Value object
class Email:
    def __init__(self, value: str):
        self._value = self._validate(value)
    
    def _validate(self, value: str) -> str:
        if not value or '@' not in value:
            raise ValueError("Invalid email format")
        return value.lower().strip()
    
    @property
    def value(self) -> str:
        return self._value
    
    def __eq__(self, other) -> bool:
        return isinstance(other, Email) and self._value == other._value
    
    def __hash__(self) -> int:
        return hash(self._value)

# Application use case
class CreateUserUseCase:
    def __init__(self,
                 user_repository: UserRepository,
                 email_service: EmailService,
                 unit_of_work: UnitOfWork):
        self._user_repository = user_repository
        self._email_service = email_service
        self._unit_of_work = unit_of_work
    
    async def execute(self, command: CreateUserCommand) -> UserDto:
        async with self._unit_of_work:
            # Check if user already exists
            existing = await self._user_repository.get_by_email(command.email)
            if existing:
                raise UserAlreadyExistsError(command.email)
            
            # Create domain entity
            user_id = UserId.generate()
            email = Email(command.email)
            user = User(user_id, email, command.username)
            
            # Save user
            await self._user_repository.save(user)
            
            # Commit transaction
            await self._unit_of_work.commit()
            
            # Handle domain events
            for event in user.get_domain_events():
                await self._handle_domain_event(event)
            
            user.clear_domain_events()
            
            return UserDto.from_entity(user)
    
    async def _handle_domain_event(self, event: DomainEvent):
        if isinstance(event, UserCreatedEvent):
            await self._email_service.send_welcome_email(event.email)
```

### Node.js (Hexagonal Architecture with NestJS)
```typescript
// src/domain/user/user.entity.ts
export class User {
    private constructor(
        private readonly _id: UserId,
        private _email: Email,
        private _username: Username,
        private readonly _createdAt: Date = new Date()
    ) {}
    
    static create(email: string, username: string): User {
        return new User(
            UserId.generate(),
            Email.create(email),
            Username.create(username)
        );
    }
    
    static fromPersistence(data: UserPersistenceData): User {
        return new User(
            UserId.fromString(data.id),
            Email.create(data.email),
            Username.create(data.username),
            data.createdAt
        );
    }
    
    get id(): UserId { return this._id; }
    get email(): Email { return this._email; }
    get username(): Username { return this._username; }
    
    changeEmail(newEmail: string): void {
        const email = Email.create(newEmail);
        if (this._email.equals(email)) return;
        
        this._email = email;
        // Emit domain event
        DomainEvents.raise(new UserEmailChanged(this._id, email));
    }
    
    toSnapshot(): UserSnapshot {
        return {
            id: this._id.value,
            email: this._email.value,
            username: this._username.value,
            createdAt: this._createdAt
        };
    }
}

// src/domain/user/value-objects/email.ts
export class Email {
    private constructor(private readonly _value: string) {}
    
    static create(email: string): Email {
        if (!this.isValid(email)) {
            throw new InvalidEmailError(email);
        }
        return new Email(email.toLowerCase().trim());
    }
    
    private static isValid(email: string): boolean {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }
    
    get value(): string { return this._value; }
    
    equals(other: Email): boolean {
        return this._value === other._value;
    }
}

// src/application/use-cases/create-user.use-case.ts
@Injectable()
export class CreateUserUseCase {
    constructor(
        @Inject('USER_REPOSITORY')
        private readonly userRepository: UserRepository,
        @Inject('EMAIL_SERVICE')
        private readonly emailService: EmailService,
        @Inject('UNIT_OF_WORK')
        private readonly unitOfWork: UnitOfWork
    ) {}
    
    async execute(command: CreateUserCommand): Promise<UserResponse> {
        await this.unitOfWork.transaction(async () => {
            // Validate business rules
            const existingUser = await this.userRepository.findByEmail(command.email);
            if (existingUser) {
                throw new UserAlreadyExistsError(command.email);
            }
            
            // Create domain entity
            const user = User.create(command.email, command.username);
            
            // Persist
            await this.userRepository.save(user);
            
            // Return response
            return UserResponse.fromEntity(user);
        });
    }
}

// src/infrastructure/persistence/typeorm-user.repository.ts
@Injectable()
export class TypeOrmUserRepository implements UserRepository {
    constructor(
        @InjectRepository(UserEntity)
        private readonly repository: Repository<UserEntity>
    ) {}
    
    async findByEmail(email: string): Promise<User | null> {
        const entity = await this.repository.findOne({ 
            where: { email: email.toLowerCase() } 
        });
        
        return entity ? User.fromPersistence({
            id: entity.id,
            email: entity.email,
            username: entity.username,
            createdAt: entity.createdAt
        }) : null;
    }
    
    async save(user: User): Promise<void> {
        const snapshot = user.toSnapshot();
        const entity = this.repository.create({
            id: snapshot.id,
            email: snapshot.email,
            username: snapshot.username,
            createdAt: snapshot.createdAt
        });
        
        await this.repository.save(entity);
    }
}

// src/infrastructure/web/controllers/user.controller.ts
@Controller('users')
@ApiTags('users')
export class UserController {
    constructor(
        private readonly createUserUseCase: CreateUserUseCase
    ) {}
    
    @Post()
    @ApiOperation({ summary: 'Create a new user' })
    @ApiResponse({ status: 201, type: UserResponse })
    async createUser(@Body() request: CreateUserRequest): Promise<UserResponse> {
        const command = new CreateUserCommand(request.email, request.username);
        return await this.createUserUseCase.execute(command);
    }
}
```

### C# (Clean Architecture with .NET Core)
```csharp
// Domain/Entities/User.cs
public class User : Entity<UserId>
{
    private readonly List<DomainEvent> _domainEvents = new();
    
    private User(UserId id, Email email, Username username) : base(id)
    {
        Email = email;
        Username = username;
        CreatedAt = DateTime.UtcNow;
    }
    
    public static User Create(string email, string username)
    {
        var userId = UserId.NewId();
        var emailVo = Email.Create(email);
        var usernameVo = Username.Create(username);
        
        var user = new User(userId, emailVo, usernameVo);
        user.AddDomainEvent(new UserCreatedEvent(userId, emailVo));
        
        return user;
    }
    
    public Email Email { get; private set; }
    public Username Username { get; private set; }
    public DateTime CreatedAt { get; private set; }
    
    public void ChangeEmail(string newEmail)
    {
        var email = Email.Create(newEmail);
        if (Email.Equals(email)) return;
        
        var oldEmail = Email;
        Email = email;
        
        AddDomainEvent(new UserEmailChangedEvent(Id, oldEmail, email));
    }
    
    public IReadOnlyList<DomainEvent> GetDomainEvents() => _domainEvents.AsReadOnly();
    
    public void ClearDomainEvents() => _domainEvents.Clear();
    
    private void AddDomainEvent(DomainEvent domainEvent) => _domainEvents.Add(domainEvent);
}

// Domain/ValueObjects/Email.cs
public record Email
{
    private Email(string value) => Value = value;
    
    public string Value { get; }
    
    public static Email Create(string email)
    {
        if (string.IsNullOrWhiteSpace(email))
            throw new ArgumentException("Email cannot be empty", nameof(email));
        
        email = email.Trim().ToLowerInvariant();
        
        if (!IsValidEmailFormat(email))
            throw new DomainException($"Invalid email format: {email}");
        
        return new Email(email);
    }
    
    private static bool IsValidEmailFormat(string email)
    {
        return Regex.IsMatch(email, @"^[^@\s]+@[^@\s]+\.[^@\s]+$");
    }
    
    public static implicit operator string(Email email) => email.Value;
}

// Application/UseCases/CreateUserUseCase.cs
public class CreateUserUseCase : ICreateUserUseCase
{
    private readonly IUserRepository _userRepository;
    private readonly IEmailService _emailService;
    private readonly IUnitOfWork _unitOfWork;
    private readonly IDomainEventDispatcher _eventDispatcher;
    
    public CreateUserUseCase(
        IUserRepository userRepository,
        IEmailService emailService,
        IUnitOfWork unitOfWork,
        IDomainEventDispatcher eventDispatcher)
    {
        _userRepository = userRepository;
        _emailService = emailService;
        _unitOfWork = unitOfWork;
        _eventDispatcher = eventDispatcher;
    }
    
    public async Task<Result<UserDto>> ExecuteAsync(CreateUserCommand command)
    {
        try
        {
            // Check business rules
            var existingUser = await _userRepository.GetByEmailAsync(command.Email);
            if (existingUser != null)
            {
                return Result<UserDto>.Failure(new UserAlreadyExistsError(command.Email));
            }
            
            // Create domain entity
            var user = User.Create(command.Email, command.Username);
            
            // Persist
            await _userRepository.AddAsync(user);
            await _unitOfWork.SaveChangesAsync();
            
            // Dispatch domain events
            await _eventDispatcher.DispatchAsync(user.GetDomainEvents());
            user.ClearDomainEvents();
            
            // Return result
            var userDto = UserDto.FromEntity(user);
            return Result<UserDto>.Success(userDto);
        }
        catch (Exception ex)
        {
            return Result<UserDto>.Failure(new UnexpectedError(ex.Message));
        }
    }
}

// Infrastructure/Persistence/EfUserRepository.cs
public class EfUserRepository : IUserRepository
{
    private readonly AppDbContext _context;
    
    public EfUserRepository(AppDbContext context)
    {
        _context = context;
    }
    
    public async Task<User?> GetByIdAsync(UserId id)
    {
        var entity = await _context.Users
            .FirstOrDefaultAsync(u => u.Id == id.Value);
        
        return entity?.ToDomainEntity();
    }
    
    public async Task<User?> GetByEmailAsync(string email)
    {
        var entity = await _context.Users
            .FirstOrDefaultAsync(u => u.Email == email.ToLowerInvariant());
        
        return entity?.ToDomainEntity();
    }
    
    public async Task AddAsync(User user)
    {
        var entity = UserEntity.FromDomainEntity(user);
        await _context.Users.AddAsync(entity);
    }
}

// Infrastructure/Web/Controllers/UsersController.cs
[ApiController]
[Route("api/[controller]")]
public class UsersController : ControllerBase
{
    private readonly ICreateUserUseCase _createUserUseCase;
    
    public UsersController(ICreateUserUseCase createUserUseCase)
    {
        _createUserUseCase = createUserUseCase;
    }
    
    [HttpPost]
    [ProducesResponseType(typeof(UserDto), StatusCodes.Status201Created)]
    [ProducesResponseType(typeof(ErrorResponse), StatusCodes.Status400BadRequest)]
    public async Task<IActionResult> CreateUser([FromBody] CreateUserRequest request)
    {
        var command = new CreateUserCommand(request.Email, request.Username);
        var result = await _createUserUseCase.ExecuteAsync(command);
        
        return result.IsSuccess
            ? CreatedAtAction(nameof(GetUser), new { id = result.Value.Id }, result.Value)
            : BadRequest(new ErrorResponse(result.Error.Message));
    }
}
```

---

## Dylan's Architecture Assessment Tools

### SOLID Principles Checker
```python
# Automated SOLID principles analysis
class SOLIDAnalyzer:
    def analyze_class(self, class_obj) -> Dict[str, bool]:
        return {
            'single_responsibility': self._check_srp(class_obj),
            'open_closed': self._check_ocp(class_obj),
            'liskov_substitution': self._check_lsp(class_obj),
            'interface_segregation': self._check_isp(class_obj),
            'dependency_inversion': self._check_dip(class_obj)
        }
    
    def _check_srp(self, class_obj) -> bool:
        """Single Responsibility: Class should have one reason to change"""
        methods = [m for m in dir(class_obj) if not m.startswith('_')]
        
        # Heuristic: too many public methods might indicate multiple responsibilities
        if len(methods) > 10:
            return False
        
        # Check for mixed concerns (e.g., persistence + business logic)
        has_business_logic = any('calculate' in m or 'process' in m for m in methods)
        has_persistence = any('save' in m or 'load' in m or 'delete' in m for m in methods)
        has_ui_logic = any('render' in m or 'display' in m for m in methods)
        
        concerns = sum([has_business_logic, has_persistence, has_ui_logic])
        return concerns <= 1
    
    def _check_dip(self, class_obj) -> bool:
        """Dependency Inversion: Depend on abstractions, not concretions"""
        import inspect
        
        # Check constructor parameters for concrete dependencies
        try:
            signature = inspect.signature(class_obj.__init__)
            for param in signature.parameters.values():
                if param.annotation and hasattr(param.annotation, '__name__'):
                    # Concrete class dependency detected
                    if not (param.annotation.__name__.startswith('I') or 
                           param.annotation.__name__.endswith('Interface') or
                           inspect.isabstract(param.annotation)):
                        return False
            return True
        except:
            return True  # Can't analyze, assume it's fine
```

### Design Pattern Recognition
```python
# Design pattern detection
class DesignPatternDetector:
    def detect_patterns(self, code_module) -> List[str]:
        patterns = []
        
        # Repository pattern
        if self._has_repository_pattern(code_module):
            patterns.append('Repository')
        
        # Factory pattern
        if self._has_factory_pattern(code_module):
            patterns.append('Factory')
        
        # Observer pattern
        if self._has_observer_pattern(code_module):
            patterns.append('Observer')
        
        # Strategy pattern
        if self._has_strategy_pattern(code_module):
            patterns.append('Strategy')
        
        return patterns
    
    def _has_repository_pattern(self, module) -> bool:
        # Look for repository interfaces and implementations
        classes = [obj for name, obj in inspect.getmembers(module, inspect.isclass)]
        
        repo_interfaces = [cls for cls in classes if 
                          'Repository' in cls.__name__ and 
                          inspect.isabstract(cls)]
        
        repo_implementations = [cls for cls in classes if
                               'Repository' in cls.__name__ and
                               not inspect.isabstract(cls)]
        
        return len(repo_interfaces) > 0 and len(repo_implementations) > 0
    
    def _has_factory_pattern(self, module) -> bool:
        classes = [obj for name, obj in inspect.getmembers(module, inspect.isclass)]
        
        # Look for factory methods or classes
        for cls in classes:
            methods = [method for method in dir(cls) if not method.startswith('_')]
            if any('create' in method.lower() or 'factory' in method.lower() for method in methods):
                return True
        
        return False
```

---

## Dylan's Architecture Recommendations

### 1. **Layered Architecture Guidelines**
```
┌─────────────────────────────────────┐
│           Presentation Layer        │  ← Controllers, Views, DTOs
├─────────────────────────────────────┤
│           Application Layer         │  ← Use Cases, Services, Commands
├─────────────────────────────────────┤
│            Domain Layer             │  ← Entities, Value Objects, Rules
├─────────────────────────────────────┤
│         Infrastructure Layer        │  ← Repositories, External APIs
└─────────────────────────────────────┘

Dependencies flow inward only!
```

### 2. **Dependency Injection Best Practices**
- **Register interfaces, not implementations**
- **Use constructor injection for required dependencies**
- **Avoid service locator anti-pattern**
- **Configure lifetime scopes appropriately** (Singleton, Scoped, Transient)
- **Validate dependencies at startup**

### 3. **Error Handling Strategy**
- **Define clear exception hierarchy**
- **Use Result pattern for expected failures**
- **Handle errors at appropriate boundaries**
- **Log errors with sufficient context**
- **Never swallow exceptions silently**

### 4. **Domain Modeling Guidelines**
- **Rich domain model with behavior**
- **Encapsulate business rules in entities**
- **Use value objects for domain concepts**
- **Implement domain events for side effects**
- **Aggregate boundaries protect invariants**

---

## Dylan's Architecture Checklist

### SOLID Principles
- [ ] **Single Responsibility** - Each class has one reason to change
- [ ] **Open/Closed** - Open for extension, closed for modification
- [ ] **Liskov Substitution** - Subtypes must be substitutable for base types
- [ ] **Interface Segregation** - Clients shouldn't depend on unused interfaces
- [ ] **Dependency Inversion** - Depend on abstractions, not concretions

### Clean Architecture
- [ ] **Dependency Direction** - Dependencies point inward toward domain
- [ ] **Layer Separation** - Clear boundaries between layers
- [ ] **Domain Isolation** - Business logic independent of frameworks
- [ ] **Interface Abstractions** - Use contracts for external dependencies
- [ ] **Testability** - All layers can be unit tested in isolation

### Design Patterns
- [ ] **Repository Pattern** - Data access abstraction
- [ ] **Unit of Work** - Transaction management
- [ ] **Factory Pattern** - Complex object creation
- [ ] **Strategy Pattern** - Algorithm variations
- [ ] **Observer Pattern** - Event-driven communication

### Error Handling
- [ ] **Consistent Strategy** - Uniform error handling approach
- [ ] **Proper Logging** - Sufficient context for debugging
- [ ] **Graceful Degradation** - Fail gracefully, not catastrophically
- [ ] **User-Friendly Messages** - Clear error communication
- [ ] **Recovery Mechanisms** - Retry policies, circuit breakers

---

## Dylan's Architecture Wisdom

*"Great architecture is invisible when everything works and invaluable when everything breaks. It's not about following every pattern or principle religiously—it's about making conscious trade-offs that serve your specific context. A well-architected system feels inevitable: each piece fits naturally, dependencies flow logically, and changes ripple predictably. Remember: architecture is not about writing code, it's about organizing code so that future-you can understand and modify it without cursing past-you."*

**The Architecture Golden Rules:**
1. **Make the implicit explicit** - Clear contracts, obvious dependencies
2. **Separate concerns ruthlessly** - Each layer, class, method has one job
3. **Depend on abstractions** - Interfaces are more stable than implementations
4. **Test at the boundaries** - Architecture quality shows in testability
5. **Optimize for change** - Code is written once, modified many times
6. **Keep it simple** - Complex solutions create more problems than they solve

---

*Remember: Architecture is the art of making the complex simple, not the simple complex. Design for the humans who will maintain your code—including future you.*