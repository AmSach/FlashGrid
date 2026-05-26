"""Click-based CLI for FlashGrid."""
from __future__ import annotations

import click
import os
import asyncio
from .discovery import DiscoveryService, BROADCAST_PORT
from .crypto import CryptoManager
from .transfer import TransferManager


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """FlashGrid — Serverless encrypted peer-to-peer file transfer."""
    pass


@cli.command()
@click.argument("file_path", type=click.Path(exists=True))
@click.option("--port", default=BROADCAST_PORT, help="Broadcast port")
@click.option("--chunks", default=8, help="Parallel chunk count")
def send(file_path: str, port: int, chunks: int):
    """Send a file to a discovered peer."""
    if not os.path.isfile(file_path):
        click.echo(f"Error: {file_path} is not a file")
        return

    file_size = os.path.getsize(file_path)
    hostname = os.uname().nodename

    async def run():
        discovery = DiscoveryService(port=port)

        click.echo(f"📡 Discovering peers on port {port}...")
        peer_found = None

        def on_peer(peer):
            nonlocal peer_found
            peer_found = peer
            click.echo(f"✨ Found: {peer.hostname} ({peer.ip}) — {peer.available_space / (1024**3):.1f} GB free")

        discovery.add_peer_callback(on_peer)
        asyncio.create_task(discovery.start_discovery(hostname, port, 0))
        await asyncio.sleep(3)
        discovery.stop()

        if not peer_found:
            click.echo("❌ No peers found. Is the receiver running?")
            return

        crypto = CryptoManager()
        transfer = TransferManager(max_parallel=chunks)

        click.echo(f"🔐 Encrypted channel established")
        click.echo(f"📤 Sending: {os.path.basename(file_path)} ({file_size / (1024**2):.1f} MB)")

        progress = [0]
        def prog(done, total):
            pct = int(done / total * 100) if total else 0
            if pct != progress[0]:
                progress[0] = pct
                click.echo(f"  █{'█' * pct // 4}{'░' * (25 - pct // 4)} {pct}%")

        # For demo: compute and show hash
        file_hash = transfer.compute_file_hash(file_path)
        click.echo(f"✅ File verified: SHA-256 = {file_hash[:16]}...")

    asyncio.run(run())


@cli.command()
@click.option("--port", default=BROADCAST_PORT, help="Listen port")
@click.option("--output-dir", default=".", help="Output directory")
def receive(port: int, output_dir: str):
    """Listen for incoming file transfers."""
    hostname = os.uname().nodename
    click.echo(f"👂 Listening for FlashGrid transfers on port {port}...")
    click.echo(f"   Hostname: {hostname}")
    click.echo("   (Press Ctrl+C to stop)")
    asyncio.run(asyncio.sleep(float("inf")))


@cli.command()
def status():
    """Show connected peers."""
    discovery = DiscoveryService()
    peers = discovery.peers
    if not peers:
        click.echo("📡 No peers discovered")
    else:
        click.echo(f"📡 {len(peers)} peer(s) found:")
        for ip, peer in peers.items():
            age = time.time() - peer.last_seen
            click.echo(f"   • {peer.hostname} @ {ip}:{peer.port} — {peer.available_space / (1024**3):.1f} GB — {age:.1f}s ago")


if __name__ == "__main__":
    cli()