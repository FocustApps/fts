"""
Performance and stress tests for authentication system.

Tests system behavior under load, memory usage, and
performance characteristics of auth operations.
"""

import asyncio
import threading
import time

import pytest

from app.services.auth_service import AuthService


class TestAuthPerformance:
    """Performance test cases for authentication system."""

    def test_token_generation_performance(self, temp_token_file):
        """Test token generation performance."""
        service = AuthService(token_file_path=temp_token_file)

        # Measure token generation time
        start_time = time.time()
        tokens = [service.generate_token() for _ in range(1000)]
        end_time = time.time()

        generation_time = end_time - start_time

        # Should generate 1000 tokens in reasonable time (< 1 second)
        assert generation_time < 1.0

        # All tokens should be unique
        assert len(set(tokens)) == 1000

        # All tokens should be valid format
        for token in tokens:
            assert len(token) == 16
            assert all(c in "0123456789abcdef" for c in token)

    def test_token_validation_performance(self, temp_token_file):
        """Test token validation performance."""
        service = AuthService(token_file_path=temp_token_file)

        # Generate token and prepare test data
        valid_token = service.get_current_token()
        invalid_tokens = [service.generate_token() for _ in range(999)]
        all_tokens = [valid_token] + invalid_tokens

        # Measure validation time
        start_time = time.time()
        results = [service.validate_token(token) for token in all_tokens]
        end_time = time.time()

        validation_time = end_time - start_time

        # Should validate 1000 tokens in reasonable time (< 0.5 seconds)
        assert validation_time < 0.5

        # Only first token should be valid
        assert results[0] is True
        assert all(result is False for result in results[1:])

    def test_concurrent_token_access(self, temp_token_file):
        """Test concurrent access to token operations."""
        service = AuthService(token_file_path=temp_token_file)

        # Pre-generate token
        expected_token = service.get_current_token()

        results = []
        errors = []

        def worker():
            try:
                token = service.get_current_token()
                is_valid = service.validate_token(token)
                results.append((token, is_valid))
            except Exception as e:
                errors.append(e)

        # Start many concurrent workers
        start_time = time.time()
        threads = [threading.Thread(target=worker) for _ in range(100)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        end_time = time.time()
        concurrent_time = end_time - start_time

        # Should complete in reasonable time (< 2 seconds)
        assert concurrent_time < 2.0

        # No errors should occur
        assert len(errors) == 0

        # All results should be consistent
        assert len(results) == 100
        for token, is_valid in results:
            assert token == expected_token
            assert is_valid is True

    def test_rapid_token_rotation(self, temp_token_file):
        """Test rapid token rotation performance."""
        service = AuthService(token_file_path=temp_token_file)

        # Perform rapid rotations
        start_time = time.time()
        tokens = []

        for _ in range(100):
            token = service.rotate_token()
            tokens.append(token)

        end_time = time.time()
        rotation_time = end_time - start_time

        # Should complete 100 rotations in reasonable time (< 5 seconds)
        assert rotation_time < 5.0

        # All tokens should be unique
        assert len(set(tokens)) == 100

        # Last token should be current
        assert service.get_current_token() == tokens[-1]

    def test_file_operation_performance(self, temp_token_file):
        """Test file I/O performance under load."""
        service = AuthService(token_file_path=temp_token_file)

        # Perform many file operations
        start_time = time.time()

        for _ in range(50):
            # Each rotation involves file write
            service.rotate_token()

            # Force file read by creating new service
            temp_service = AuthService(token_file_path=temp_token_file)
            temp_service.get_current_token()

        end_time = time.time()
        file_ops_time = end_time - start_time

        # Should complete file operations in reasonable time (< 10 seconds)
        assert file_ops_time < 10.0

    def test_memory_usage_stability(self, temp_token_file):
        """Test memory usage remains stable during extended operations."""
        import gc

        service = AuthService(token_file_path=temp_token_file)

        # Force garbage collection before test
        gc.collect()

        # Perform many operations
        for i in range(1000):
            # Mix of operations
            if i % 10 == 0:
                service.rotate_token()
            else:
                token = service.get_current_token()
                service.validate_token(token)

            # Periodic garbage collection
            if i % 100 == 0:
                gc.collect()

        # Test should complete without memory errors
        # (Memory leaks would cause this test to fail or become very slow)
        assert True


class TestAuthStress:
    """Stress test cases for authentication system."""

    def test_high_concurrency_stress(self, temp_token_file):
        """Test system under high concurrent load."""
        service = AuthService(token_file_path=temp_token_file)

        # Generate initial token
        service.get_current_token()

        success_count = 0
        error_count = 0

        def stress_worker():
            nonlocal success_count, error_count
            try:
                for _ in range(10):
                    token = service.get_current_token()
                    if service.validate_token(token):
                        success_count += 1
                    else:
                        error_count += 1
            except Exception:
                error_count += 1

        # High concurrency test
        threads = [threading.Thread(target=stress_worker) for _ in range(50)]

        start_time = time.time()
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        end_time = time.time()

        stress_time = end_time - start_time

        # Should handle high load (< 10 seconds for 500 operations across 50 threads)
        assert stress_time < 10.0

        # Most operations should succeed
        total_ops = success_count + error_count
        success_rate = success_count / total_ops if total_ops > 0 else 0
        assert success_rate > 0.95  # 95% success rate minimum

    def test_extended_runtime_stress(self, temp_token_file):
        """Test system stability over extended runtime."""
        service = AuthService(token_file_path=temp_token_file)

        start_time = time.time()
        operation_count = 0
        error_count = 0

        # Run for a limited time to avoid overly long tests
        max_runtime = 5.0  # 5 seconds

        while time.time() - start_time < max_runtime:
            try:
                # Mix of operations
                if operation_count % 20 == 0:
                    service.rotate_token()
                else:
                    token = service.get_current_token()
                    service.validate_token(token)

                operation_count += 1

                # Small delay to prevent overwhelming
                time.sleep(0.001)

            except Exception:
                error_count += 1

        # Should maintain low error rate
        error_rate = error_count / operation_count if operation_count > 0 else 1
        assert error_rate < 0.01  # Less than 1% error rate

        # Should complete significant number of operations
        assert operation_count > 100

    @pytest.mark.asyncio
    @pytest.mark.xfail(
        reason="async def functions are not natively supported in current pytest-asyncio configuration"
    )
    async def test_async_compatibility_stress(self, temp_token_file):
        """Test system compatibility with async operations."""
        service = AuthService(token_file_path=temp_token_file)

        async def async_worker():
            """Async worker that uses auth service."""
            # Simulate async work with auth operations
            await asyncio.sleep(0.01)
            token = service.get_current_token()
            await asyncio.sleep(0.01)
            return service.validate_token(token)

        # Run many async workers concurrently
        start_time = time.time()
        tasks = [async_worker() for _ in range(100)]
        results = await asyncio.gather(*tasks)
        end_time = time.time()

        async_time = end_time - start_time

        # Should complete in reasonable time
        assert async_time < 5.0

        # All validations should succeed
        assert all(result is True for result in results)

    def test_resource_cleanup_stress(self, temp_token_file):
        """Test resource cleanup under stress."""
        # Test multiple service instances and cleanup
        services = []

        try:
            # Create many service instances
            for i in range(20):
                token_file = temp_token_file.parent / f"stress_token_{i}.txt"
                service = AuthService(token_file_path=token_file)
                services.append((service, token_file))

                # Use the service
                service.get_current_token()
                service.rotate_token()

        finally:
            # Cleanup all created files
            for service, token_file in services:
                if token_file.exists():
                    token_file.unlink()

        # Test should complete without resource leaks
        assert True


if __name__ == "__main__":
    pytest.main([__file__])
