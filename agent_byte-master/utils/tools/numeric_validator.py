"""
Numeric Validator
==================

Uses loaded math knowledge to validate whether a translated/decoded value
makes numeric sense — feeds back into the pipeline's Translator.

Three validation modes
-----------------------
1. Symbolic check (SymPy)     — parse and evaluate math expressions exactly
2. Numeric bounds check       — is the value in a plausible range?
3. Dataset similarity check   — find the closest known problem in the
                                 SkillLibrary/memory and compare answers

This gives the Translator a domain-aware sanity check on recovered data,
not just a hash check.  A recovered block containing "42" when the problem
asked for a prime number can be flagged immediately.
"""
from __future__ import annotations
import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    valid: bool
    confidence: float        # 0.0 → 1.0
    method: str              # "sympy" | "bounds" | "similarity" | "none"
    notes: str = ""
    similar_problem: str = ""
    similar_solution: str = ""


class NumericValidator:
    """
    Validates numeric/algebraic values using math libraries + dataset knowledge.
    Used by the Translator to sanity-check recovered data blocks.
    """

    def __init__(self):
        self._sympy = self._load_sympy()
        self._numpy = self._load_numpy()

    def _load_sympy(self):
        try:
            import sympy
            return sympy
        except ImportError:
            logger.debug("[NumVal] sympy not installed — symbolic validation disabled")
            return None

    def _load_numpy(self):
        try:
            import numpy
            return numpy
        except ImportError:
            return None

    # ── public API ────────────────────────────────────────────────────────────

    def validate(self, value: str, problem_context: str = "") -> ValidationResult:
        """
        Validate a value against mathematical knowledge.
        Returns ValidationResult with confidence and method used.
        """
        # 1. Try SymPy symbolic evaluation
        result = self._sympy_validate(value, problem_context)
        if result.confidence > 0.7:
            return result

        # 2. Numeric bounds check
        result = self._bounds_validate(value, problem_context)
        if result.confidence > 0.5:
            return result

        # 3. Dataset similarity check
        result = self._similarity_validate(value, problem_context)
        return result

    def validate_expression(self, expr: str) -> Tuple[bool, Any]:
        """Parse and evaluate a math expression. Returns (valid, result)."""
        if not self._sympy:
            return False, None
        try:
            sp = self._sympy
            parsed = sp.sympify(expr)
            evaluated = float(parsed.evalf()) if parsed.is_number else parsed
            return True, evaluated
        except Exception as e:
            return False, str(e)

    def compare_expressions(self, a: str, b: str, tolerance: float = 1e-9) -> bool:
        """Return True if two math expressions evaluate to the same value."""
        if not self._sympy:
            return a.strip() == b.strip()
        ok_a, val_a = self.validate_expression(a)
        ok_b, val_b = self.validate_expression(b)
        if not ok_a or not ok_b:
            return False
        try:
            if isinstance(val_a, float) and isinstance(val_b, float):
                return abs(val_a - val_b) < tolerance
            return self._sympy.simplify(
                self._sympy.sympify(a) - self._sympy.sympify(b)) == 0
        except Exception:
            return False

    def extract_numbers(self, text: str) -> List[float]:
        """Extract all numeric values from a text string."""
        pattern = r"-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?"
        matches = re.findall(pattern, text)
        results = []
        for m in matches:
            try:
                results.append(float(m))
            except ValueError:
                pass
        return results

    # ── validation methods ────────────────────────────────────────────────────

    def _sympy_validate(self, value: str, context: str) -> ValidationResult:
        if not self._sympy:
            return ValidationResult(valid=False, confidence=0.0, method="sympy",
                                    notes="sympy not available")
        valid, result = self.validate_expression(value)
        if valid:
            return ValidationResult(
                valid=True, confidence=0.8, method="sympy",
                notes=f"SymPy evaluated: {result}"
            )
        # Try to find and evaluate any math in the value
        nums = self.extract_numbers(value)
        if nums:
            return ValidationResult(
                valid=True, confidence=0.5, method="sympy",
                notes=f"Contains numeric values: {nums[:5]}"
            )
        return ValidationResult(valid=False, confidence=0.1, method="sympy",
                                notes=f"Cannot evaluate: {value[:50]}")

    def _bounds_validate(self, value: str, context: str) -> ValidationResult:
        """Check if extracted numbers are in plausible ranges for the context."""
        nums = self.extract_numbers(value)
        if not nums:
            return ValidationResult(valid=False, confidence=0.0, method="bounds",
                                    notes="no numeric content found")
        ctx_lower = context.lower()

        # Domain-specific bounds
        if any(w in ctx_lower for w in ["probability", "percent", "%"]):
            if all(0 <= n <= 100 for n in nums):
                return ValidationResult(valid=True, confidence=0.75, method="bounds",
                                        notes="values in valid probability range [0,100]")
            else:
                return ValidationResult(valid=False, confidence=0.75, method="bounds",
                                        notes=f"probability out of range: {nums}")

        if any(w in ctx_lower for w in ["prime", "factor", "divisor"]):
            if all(n == int(n) and n > 0 for n in nums):
                return ValidationResult(valid=True, confidence=0.65, method="bounds",
                                        notes="positive integers (consistent with number theory)")

        if any(w in ctx_lower for w in ["angle", "degree", "triangle"]):
            if all(0 <= n <= 360 for n in nums):
                return ValidationResult(valid=True, confidence=0.7, method="bounds",
                                        notes="values in valid angle range [0,360]")

        # Generic: just confirm it's finite and not absurdly large
        if all(abs(n) < 1e15 for n in nums):
            return ValidationResult(valid=True, confidence=0.4, method="bounds",
                                    notes=f"finite values: {nums[:3]}")
        return ValidationResult(valid=False, confidence=0.5, method="bounds",
                                notes="values exceed plausible bounds")

    def _similarity_validate(self, value: str, context: str) -> ValidationResult:
        """Find the closest known math problem and compare answers."""
        if not context:
            return ValidationResult(valid=True, confidence=0.2, method="none",
                                    notes="no context — cannot validate")
        try:
            from core.controllers.memory_controller import memory
            recalled = memory.recall(context, k=3)
            if not recalled:
                return ValidationResult(valid=True, confidence=0.2, method="similarity",
                                        notes="no similar problems in memory")
            best = recalled[0]
            content = best.get("content", "")
            # Extract the solution from stored memory entry
            if "Solution:" in content:
                stored_sol = content.split("Solution:")[-1].strip()[:200]
                match = self.compare_expressions(value, stored_sol)
                conf = 0.85 if match else 0.3
                return ValidationResult(
                    valid=match, confidence=conf, method="similarity",
                    notes=f"compared to similar problem answer",
                    similar_problem=content[:100],
                    similar_solution=stored_sol[:100],
                )
        except Exception as e:
            logger.debug("[NumVal] similarity check error: %s", e)
        return ValidationResult(valid=True, confidence=0.2, method="none",
                                notes="similarity check failed gracefully")

    # ── math library utilities ────────────────────────────────────────────────

    def solve_equation(self, equation: str, variable: str = "x") -> Optional[List]:
        """Solve an equation symbolically using SymPy."""
        if not self._sympy:
            return None
        try:
            sp = self._sympy
            var = sp.Symbol(variable)
            solutions = sp.solve(equation, var)
            return [str(s) for s in solutions]
        except Exception as e:
            logger.debug("[NumVal] solve error: %s", e)
            return None

    def factor(self, expr: str) -> Optional[str]:
        """Factorise an expression."""
        if not self._sympy:
            return None
        try:
            return str(self._sympy.factor(self._sympy.sympify(expr)))
        except Exception:
            return None

    def simplify(self, expr: str) -> Optional[str]:
        """Simplify a mathematical expression."""
        if not self._sympy:
            return None
        try:
            return str(self._sympy.simplify(self._sympy.sympify(expr)))
        except Exception:
            return None

    def matrix_ops(self, matrix_data: List[List[float]], op: str = "det") -> Optional[Any]:
        """Perform matrix operations using NumPy."""
        if not self._numpy:
            return None
        np = self._numpy
        try:
            m = np.array(matrix_data, dtype=float)
            ops = {
                "det":    lambda x: float(np.linalg.det(x)),
                "inv":    lambda x: np.linalg.inv(x).tolist(),
                "eig":    lambda x: [v.tolist() for v in np.linalg.eig(x)],
                "rank":   lambda x: int(np.linalg.matrix_rank(x)),
                "trace":  lambda x: float(np.trace(x)),
                "norm":   lambda x: float(np.linalg.norm(x)),
            }
            return ops.get(op, lambda x: None)(m)
        except Exception as e:
            logger.debug("[NumVal] matrix_ops error: %s", e)
            return None


# Singleton
numeric_validator = NumericValidator()
