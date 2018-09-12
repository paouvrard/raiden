from raiden.storage import wal
from raiden.transfer import node, views
from raiden.transfer.state import NettingChannelState
from raiden.transfer.utils import hash_balance_data
from raiden.utils import typing


def channel_state_until_balance_hash(
        raiden: 'RaidenService',
        token_address: typing.TokenAddress,
        channel_identifier: typing.ChannelID,
        target_balance_hash: bytes
) -> typing.Optional[NettingChannelState]:
    """ Go through WAL state changes until a certain hash balance is found. """

    # Restore state from the latest snapshot
    snapshot = raiden.wal.storage.get_latest_state_snapshot()
    last_applied_state_change_id, chain_state = snapshot
    unapplied_state_changes = raiden.wal.storage.get_statechanges_by_identifier(
        from_identifier=last_applied_state_change_id,
        to_identifier='latest',
    )
    # Create a copy WAL
    log = wal.wal_from_snapshot(node.state_transition, raiden.wal.storage, chain_state)
    for state_change in unapplied_state_changes:
        log.state_manager.dispatch(state_change)
        channel_state = views.get_channelstate_by_id(
            chain_state=chain_state,
            payment_network_id=raiden.default_registry,
            token_address=token_address,
            channel_id=channel_identifier
        )
        if not channel_state:
            continue

        partner_latest_balance_proof = channel_state.partner_state.balance_proof
        balance_hash = hash_balance_data(
            transferred_amount=partner_latest_balance_proof.transferred_amount,
            locked_amount=partner_latest_balance_proof.locked_amount,
            locksroot=partner_latest_balance_proof.locksroot
        )
        if target_balance_hash == balance_hash:
            return channel_state
    return None