"""Tests for the Hosted MT Node Provisioner."""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from engine.ta.broker.mt5.hosted.provisioner import HostedProvisioner

class TestHostedProvisioner:
    @pytest.mark.asyncio
    @patch("engine.ta.broker.mt5.hosted.provisioner.config")
    @patch("engine.ta.broker.mt5.hosted.provisioner.client")
    async def test_create_hosted_pod_mt4(self, mock_client, mock_config):
        # Mock the k8s API client
        mock_api = AsyncMock()
        
        provisioner = HostedProvisioner()
        provisioner._init_client = AsyncMock(return_value=mock_api)
        provisioner._cleanup_existing = AsyncMock()
        
        await provisioner.create_hosted_pod(
            connection_id="conn_1234567890",
            platform="mt4",
            server="MT4-Server",
            login="12345",
            password="pwd",
        )
        
        # Verify the cleanup was called
        provisioner._cleanup_existing.assert_called_once_with("etradie-mt-conn_12345678")
        
        # Verify pod creation was called
        mock_api.create_namespaced_pod.assert_called_once()
        
        # Extract the Pod manifest passed to the API
        pod_manifest = mock_api.create_namespaced_pod.call_args[1]["body"]
        
        # Verify platform env var
        env_vars = pod_manifest.spec.containers[0].env
        platform_env = next((e for e in env_vars if e.name == "MT_PLATFORM"), None)
        assert platform_env is not None
        assert platform_env.value == "mt4"

    @pytest.mark.asyncio
    @patch("engine.ta.broker.mt5.hosted.provisioner.config")
    @patch("engine.ta.broker.mt5.hosted.provisioner.client")
    async def test_create_hosted_pod_mt5(self, mock_client, mock_config):
        mock_api = AsyncMock()
        provisioner = HostedProvisioner()
        provisioner._init_client = AsyncMock(return_value=mock_api)
        provisioner._cleanup_existing = AsyncMock()
        
        await provisioner.create_hosted_pod(
            connection_id="conn_0987654321",
            platform="mt5",
            server="MT5-Server",
            login="54321",
            password="pwd",
        )
        
        mock_api.create_namespaced_pod.assert_called_once()
        pod_manifest = mock_api.create_namespaced_pod.call_args[1]["body"]
        env_vars = pod_manifest.spec.containers[0].env
        platform_env = next((e for e in env_vars if e.name == "MT_PLATFORM"), None)
        assert platform_env is not None
        assert platform_env.value == "mt5"
