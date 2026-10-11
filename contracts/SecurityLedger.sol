// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title SecurityLedger
 * @dev Notarizes IoT cybersecurity threat events and SHA-256 integrity hashes on-chain.
 */
contract SecurityLedger {
    struct SecurityEvent {
        string eventId;
        string deviceId;
        string attackType;
        string severity;
        string eventHash;
        uint256 timestamp;
        address recordedBy;
    }

    SecurityEvent[] private _events;
    mapping(string => uint256) private _eventIdToIndex;
    mapping(string => bool) private _eventExists;

    event SecurityEventRecorded(
        string indexed eventId,
        string deviceId,
        string attackType,
        string severity,
        string eventHash,
        uint256 timestamp
    );

    function recordEvent(
        string memory eventId,
        string memory deviceId,
        string memory attackType,
        string memory severity,
        string memory eventHash
    ) public returns (uint256) {
        require(!_eventExists[eventId], "Event ID already notarized");

        SecurityEvent memory newEvent = SecurityEvent({
            eventId: eventId,
            deviceId: deviceId,
            attackType: attackType,
            severity: severity,
            eventHash: eventHash,
            timestamp: block.timestamp,
            recordedBy: msg.sender
        });

        _events.push(newEvent);
        uint256 index = _events.length - 1;
        _eventIdToIndex[eventId] = index;
        _eventExists[eventId] = true;

        emit SecurityEventRecorded(
            eventId,
            deviceId,
            attackType,
            severity,
            eventHash,
            block.timestamp
        );

        return index;
    }

    function getEventCount() external view returns (uint256) {
        return _events.length;
    }

    function getEvent(uint256 index) external view returns (
        string memory eventId,
        string memory deviceId,
        string memory attackType,
        string memory severity,
        string memory eventHash,
        uint256 timestamp,
        address recordedBy
    ) {
        require(index < _events.length, "Index out of bounds");
        SecurityEvent storage ev = _events[index];
        return (
            ev.eventId,
            ev.deviceId,
            ev.attackType,
            ev.severity,
            ev.eventHash,
            ev.timestamp,
            ev.recordedBy
        );
    }

    function verifyEventHash(string memory eventId, string memory expectedHash) external view returns (bool) {
        if (!_eventExists[eventId]) return false;
        uint256 index = _eventIdToIndex[eventId];
        return keccak256(bytes(_events[index].eventHash)) == keccak256(bytes(expectedHash));
    }
}
