"""Model(s) for Player."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from mashumaro import DataClassDictMixin, field_options, pass_through

from .constants import PLAYER_CONTROL_NATIVE
from .enums import MediaType, PlayerFeature, PlayerState, PlayerType
from .unique_list import UniqueList


@dataclass(frozen=True)
class DeviceInfo(DataClassDictMixin):
    """Model for a player's deviceinfo."""

    model: str = "Unknown model"
    manufacturer: str = "Unknown Manufacturer"
    software_version: str | None = None
    model_id: str | None = None
    manufacturer_id: str | None = None
    ip_address: str | None = None
    mac_address: str | None = None

    def __post_serialize__(self, d: dict[Any, Any]) -> dict[Any, Any]:
        """Execute action(s) on serialization."""
        # TEMP 2024-11-20: add alias to 'address' for ip_address for backwards compatibility
        # Remove this in a future release
        d["address"] = d.get("ip_address") or ""
        return d


@dataclass
class PlayerMedia(DataClassDictMixin):
    """Metadata of Media loading/loaded into a player."""

    uri: str  # uri or other identifier of the loaded media
    media_type: MediaType = MediaType.UNKNOWN
    title: str | None = None  # optional
    artist: str | None = None  # optional
    album: str | None = None  # optional
    image_url: str | None = None  # optional
    duration: int | None = None  # optional
    queue_id: str | None = None  # only present for requests from queue controller
    queue_item_id: str | None = None  # only present for requests from queue controller
    custom_data: dict[str, Any] | None = None  # optional


@dataclass(frozen=True)
class PlayerSource(DataClassDictMixin):
    """Model for a player source."""

    id: str
    name: str
    # passive: this source can not be selected/activated by MA/the user
    passive: bool = False


@dataclass
class Player(DataClassDictMixin):
    """Representation of a Player within Music Assistant."""

    player_id: str
    provider: str  # instance_id of the player provider
    type: PlayerType
    name: str
    available: bool
    device_info: DeviceInfo
    supported_features: set[PlayerFeature] = field(default_factory=set)

    state: PlayerState | None = None
    elapsed_time: float | None = None
    elapsed_time_last_updated: float | None = None
    powered: bool | None = None
    volume_level: int | None = None
    volume_muted: bool | None = None

    # group_childs: Return list of player group child id's or synced child`s.
    # - If this player is a dedicated group player,
    #   returns all child id's of the players in the group.
    # - If this is a syncgroup of players from the same platform (e.g. sonos),
    #   this will return the id's of players synced to this player,
    #   and this will include the player's own id (as first item in the list).
    group_childs: UniqueList[str] = field(default_factory=UniqueList)

    # can_group_with: return set of player_id's this player can group/sync with
    # can also be instance id of an entire provider if all players can group with each other
    can_group_with: set[str] = field(default_factory=set)

    # synced_to: player_id of the player this player is currently synced to
    # also referred to as "sync leader"
    synced_to: str | None = None

    # active_source: return active source (id) for this player
    # this can be a player native source id as defined in 'source list'
    # or a Music Assistant queue id, if Music Assistant is the active source.
    # When set to known, the player provider has no accurate information about the source.
    # iN that case, the player manager will try to find out the active source.
    active_source: str | None = None

    # source_list: return list of available (native) sources for this player
    source_list: UniqueList[PlayerSource] = field(default_factory=UniqueList)

    # active_group: return player_id of the active group for this player (if any)
    # if the player is grouped and a group is active,
    # this should be set to the group's player_id by the group player implementation.
    active_group: str | None = None

    # current_media: return current active/loaded item on the player
    # this may be a MA queue item, url, uri or some provider specific string
    # includes metadata if supported by the provider/player
    current_media: PlayerMedia | None = None

    # enabled_by_default: if the player is enabled by default
    # can be used by a player provider to exclude some sort of players
    enabled_by_default: bool = True

    # needs_poll: bool that can be set by the player(provider)
    # if this player needs to be polled for state changes by the player manager
    needs_poll: bool = False

    # poll_interval: a (dynamic) interval in seconds to poll the player (used with needs_poll)
    poll_interval: int = 30

    #############################################################################
    # the fields below are managed by the player manager and config             #
    #############################################################################

    # enabled: if the player is enabled
    # will be set by the player manager based on config
    # a disabled player is hidden in the UI and updates will not be processed
    # nor will it be added to the HA integration
    enabled: bool = True

    # hidden: if the player is hidden in the UI
    # will be set by the player manager based on config
    # a hidden player is hidden in the UI only but can still be controlled
    hidden: bool = False

    # icon: material design icon for this player
    # will be set by the player manager based on config
    icon: str = "mdi-speaker"

    # group_volume: if the player is a player group or syncgroup master,
    # this will return the average volume of all child players
    # if not a group player, this is just the player's volume
    group_volume: int = 100

    # display_name: return final/corrected name of the player
    # always prefers any overridden name from settings
    display_name: str = ""

    # extra_data: any additional data to store on the player object
    # and pass along freely
    extra_data: dict[str, Any] = field(default_factory=dict)

    # announcement_in_progress: boolean to indicate there's an announcement in progress.
    announcement_in_progress: bool = False

    # power_control: the power control attached to this player (set by config)
    power_control: str = PLAYER_CONTROL_NATIVE

    # volume_control: the volume control attached to this player (set by config)
    volume_control: str = PLAYER_CONTROL_NATIVE

    # mute_control: the volume control attached to this player (set by config)
    mute_control: str = PLAYER_CONTROL_NATIVE

    #############################################################################
    # the fields below will only be used server-side and not sent to the client #
    #############################################################################

    # previous volume level is used by the player manager in case of fake muting
    previous_volume_level: int | None = field(
        default=None,
        compare=False,
        metadata=field_options(serialize="omit", deserialize=pass_through),
        repr=False,
    )

    # last_poll: when was the player last polled (used with needs_poll)
    last_poll: float = field(
        default=0.0,
        compare=False,
        metadata=field_options(serialize="omit", deserialize=pass_through),
        repr=False,
    )

    #############################################################################
    # helper methods and properties                                             #
    #############################################################################

    @property
    def corrected_elapsed_time(self) -> float | None:
        """Return the corrected/realtime elapsed time."""
        if self.elapsed_time is None or self.elapsed_time_last_updated is None:
            return None
        if self.state == PlayerState.PLAYING:
            return self.elapsed_time + (time.time() - self.elapsed_time_last_updated)
        return self.elapsed_time

    @property
    def current_item_id(self) -> str | None:
        """Return current_item_id from current_media (if exists)."""
        if self.current_media:
            return self.current_media.uri
        return None

    @current_item_id.setter
    def current_item_id(self, uri: str) -> None:
        """Set current_item_id (for backwards compatibility)."""
        self.current_media = PlayerMedia(uri)
