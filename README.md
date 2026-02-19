
# GMOS Testing Setup

This project is the setup code for GMOS testing setup, used for controlling both STM32 evaluation board and ATI to test and sample GMOS gas sensor device using a two-layer lock-in amplifier setup.

## Code Structure

```
GMOS-LIA/
├── src/
│   ├── stm32/          # STM32 evaluation board code
│   ├── ati/            # ATI control module
│   └── lia/            # Lock-in amplifier implementation
├── tests/              # Test suite
├── examples/           # Usage examples
└── README.md
```

## Running Examples

### Prerequisites
- STM32 development environment
- Python 3.8+
- Required dependencies (see requirements.txt)

### Basic Example

```bash
# Install dependencies
pip install -r requirements.txt

# Run example test
python examples/basic_test.py

# Run sensor sampling
python examples/sample_sensor.py
```

### Testing

```bash
# Run all tests
pytest tests/

# Run specific test module
pytest tests/test_lia.py -v
```
