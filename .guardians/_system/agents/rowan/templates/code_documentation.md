# Code Documentation Template (Lexicon)

## What This Covers
- Docstrings (module, class, function, method)
- Type hints (parameters, returns, variables)
- API reference documentation
- Inline comments (when necessary)

---

## Review Metrics

### Coverage
- Public functions documented: X/Y (Z%)
- Public classes documented: X/Y (Z%)
- Public methods documented: X/Y (Z%)
- Module-level docstring: Present/Missing

### Type Hints
- Complete type hints: X/Y (Z%)
- Partial type hints: X
- Missing type hints: X

### Quality
- Docstrings with examples: X/Y
- Parameter descriptions complete: X/Y
- Return value descriptions: X/Y
- Exception documentation: X/Y

---

## Documentation Style Detection

Auto-detect project style:
- **Google Style** (most common)
- **NumPy Style** (scientific Python)
- **Sphinx Style** (legacy/formal docs)
- **Mixed/None** (recommend standardizing)

---

## Common Findings Categories

### Missing Docstrings
- Public function/class has no docstring
- Docstring exists but is just a one-liner for complex function
- Module missing docstring

### Incomplete Docstrings
- Missing parameter descriptions
- Missing return value description
- Missing exception documentation
- No usage example for complex functions

### Type Hint Issues
- Missing type hints entirely
- Partial type hints (some params missing)
- Incorrect type hints (doesn't match actual usage)
- Missing return type hint

### Accuracy Issues
- Docstring doesn't match implementation
- Type hints conflict with actual usage
- Examples in docstring don't work
- Outdated parameter names in docstring

---

## Solution Templates

### Google Style Docstring (Recommended Default)

```python
def function_name(param1: str, param2: int, param3: Optional[list] = None) -> bool:
    """One-line summary (imperative mood: 'Calculate', 'Return', 'Process').
    
    Optional longer description explaining what this does, when to use it,
    and any important context or gotchas.
    
    Args:
        param1: Description of param1. Be specific about format/constraints.
        param2: Description of param2. Mention valid ranges if applicable.
        param3: Description of param3. Note it's optional and the default behavior.
    
    Returns:
        Description of what's returned. Be specific about the value, not just type.
    
    Raises:
        ValueError: When param2 is negative.
        TypeError: When param1 is not a string.
    
    Example:
        >>> function_name("test", 42)
        True
        >>> function_name("test", -1)
        ValueError: param2 must be positive
    
    Note:
        Any important notes, warnings, or related information.
    """
    pass
```

### NumPy Style Docstring (Scientific/Data Science)

```python
def function_name(param1: str, param2: int) -> np.ndarray:
    """One-line summary.
    
    Longer description if needed.
    
    Parameters
    ----------
    param1 : str
        Description of param1.
    param2 : int
        Description of param2.
    
    Returns
    -------
    np.ndarray
        Description of the array returned.
    
    Raises
    ------
    ValueError
        When param2 is invalid.
    
    Examples
    --------
    >>> function_name("test", 42)
    array([1, 2, 3])
    
    Notes
    -----
    Additional context or mathematical formulas.
    """
    pass
```

### Class Documentation

```python
class ClassName:
    """One-line description of the class.
    
    Longer description of what this class represents, its purpose,
    and how it should be used.
    
    Attributes:
        attr1: Description of public attribute.
        attr2: Description of public attribute.
    
    Example:
        >>> obj = ClassName(param1="value")
        >>> obj.method()
        'result'
    """
    
    def __init__(self, param1: str, param2: int = 0):
        """Initialize ClassName.
        
        Args:
            param1: Description.
            param2: Description. Defaults to 0.
        """
        self.attr1 = param1
        self.attr2 = param2
    
    def method(self) -> str:
        """Method description.
        
        Returns:
            Description of return value.
        """
        pass
```

### Module-Level Docstring

```python
"""Module name and one-line description.

More detailed description of what this module contains and its purpose.
Can span multiple paragraphs.

Typical usage example:

    from module import ClassName
    
    obj = ClassName()
    result = obj.method()
"""

# Module contents...
```

---

## Type Hints Best Practices

### Basic Types
```python
from typing import List, Dict, Set, Tuple, Optional, Union, Any, Callable

def example(
    name: str,
    age: int,
    scores: List[float],
    mapping: Dict[str, int],
    optional_param: Optional[str] = None,
    union_param: Union[int, str] = 0,
    callback: Optional[Callable[[str], bool]] = None
) -> Tuple[bool, str]:
    """Well-typed function."""
    pass
```

### Advanced Types (Python 3.9+)
```python
def modern_example(
    items: list[str],  # Instead of List[str]
    mapping: dict[str, int],  # Instead of Dict[str, int]
    value: str | None = None  # Instead of Optional[str]
) -> tuple[bool, str]:  # Instead of Tuple[bool, str]
    """Uses modern type hint syntax."""
    pass
```

### Generic Types
```python
from typing import TypeVar, Generic

T = TypeVar('T')

class Container(Generic[T]):
    """Generic container that works with any type."""
    
    def __init__(self, value: T):
        self.value = value
    
    def get(self) -> T:
        return self.value
```

---

## When to Add Inline Comments

**DO add comments for:**
- Complex algorithms or non-obvious logic
- Workarounds for bugs/limitations
- Performance optimizations
- Regex patterns or magic numbers
- Business logic context

**DON'T comment:**
- Obvious code (`i += 1  # increment i`)
- What the code does (docstring's job)
- Code that should be refactored to be clearer

```python
# ✅ GOOD: Explains why
# Using dict instead of set because we need to preserve insertion order
# for Python <3.7 compatibility
items = {}

# ❌ BAD: Just repeats the code
# Loop through items
for item in items:
    # Process the item
    process(item)
```

---

## Lexicon's Tone for Code Documentation

**When reviewing:**
- "This function is doing important work but future-you will have no idea what `x` is supposed to be."
- "Type hints are like a love letter to your IDE. Let's write one."
- "This docstring is technically correct, but 'does stuff' isn't exactly helpful documentation."

**When creating:**
- Be clear and specific
- Use examples liberally
- Think about the confused developer at 2am
- Write for humans, not just validators

**When the code is well-documented:**
- "Now THIS is how you document a function. Chef's kiss. 👨‍🍳💋"
- "Excellent docstring. I have nothing to add here."
- "This type hint game is strong. Respect."

---

## Finding Template (Use Standard Lexicon Format)

```markdown
### Finding #X: [e.g., "Missing docstring on public API function"]
**Severity:** [🔴/🟠/🟡/🟢] **Effort:** [Small/Medium/Large] **Risk:** [Low/Medium/High]
**Location:** `function_name` (lines X-Y)
**Category:** Missing Docstring | Incomplete Docstring | Type Hints | Accuracy

#### The Issue
[Why this matters — who's affected, what's unclear]

**Current State:**
```python
def process_user_data(data, flags=None):
    # No docstring, no type hints
    pass
```

#### Options

**Option A: Full Google-style docstring with type hints** [RECOMMENDED]
Best for public APIs and complex functions.

```python
def process_user_data(
    data: Dict[str, Any], 
    flags: Optional[List[str]] = None
) -> bool:
    """Process and validate user data.
    
    Validates the user data dictionary and applies optional flags
    to modify processing behavior.
    
    Args:
        data: User data dictionary with 'name', 'email', 'age' keys.
        flags: Optional processing flags. Supported: 'strict', 'verbose'.
    
    Returns:
        True if processing succeeded, False otherwise.
    
    Raises:
        ValueError: If required keys are missing from data.
    
    Example:
        >>> process_user_data({'name': 'Alice', 'email': 'a@b.com', 'age': 30})
        True
    """
    pass
```

**Option B: Minimal docstring (if truly simple/internal)**
Only if function is genuinely trivial or internal-only.

```python
def process_user_data(data: dict, flags: list | None = None) -> bool:
    """Validate and process user data dictionary."""
    pass
```

#### Manager Decision
- [ ] Approve A
- [ ] Approve B
- [ ] Reject (Reason: __)
- [ ] Needs Discussion

**Status:** PENDING
```

---

**Lexicon's reminder:** "Documentation isn't just for others—it's for future-you who's forgotten why you made that weird design decision at 11pm."