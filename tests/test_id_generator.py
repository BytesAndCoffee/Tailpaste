"""Property-based tests for paste ID generation.

Feature: tailscale-paste-service
"""

from hypothesis import given, strategies as st, settings
from src.id_generator import IDGenerator


class TestIDGeneratorProperties:
    """Property-based tests for ID generation."""

    @settings(max_examples=100)
    @given(st.integers(min_value=10, max_value=100))
    def test_property_3_unique_paste_id_generation(self, num_pastes):
        """Property 3: Unique paste ID generation.

        For any two pastes created by the service, their IDs should be distinct.

        Validates: Requirements 2.2

        Feature: tailscale-paste-service, Property 3: Unique paste ID generation
        """
        generator = IDGenerator()
        generated_ids = set()

        # Track which IDs exist (simulating storage)
        existing_ids = set()

        def exists_check(paste_id: str) -> bool:
            """Check if ID already exists."""
            return paste_id in existing_ids

        # Generate multiple paste IDs
        for _ in range(num_pastes):
            paste_id = generator.generate(exists_check)

            # Verify this ID hasn't been generated before
            assert paste_id not in generated_ids, f"Duplicate ID generated: {paste_id}"

            # Add to tracking sets
            generated_ids.add(paste_id)
            existing_ids.add(paste_id)

        # Verify we generated the expected number of unique IDs
        assert (
            len(generated_ids) == num_pastes
        ), f"Expected {num_pastes} unique IDs, got {len(generated_ids)}"
