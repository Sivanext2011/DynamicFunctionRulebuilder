FUNCTION DetermineChargingProfile

INPUT
    serviceType : LongNumber
    roleOfNode : IntegerNumber
    callingPartyNumber : String
    calledPartyNumber : String
    roamingIndicator : Boolean

OUTPUT
    chargingProfile : String
    ratingGroup : IntegerNumber
    serviceIdentifier : String

INTERNAL
    isInternational : Boolean

RULE

IF EXISTS roamingIndicator
    IF roamingIndicator == 1
        SET chargingProfile = "RoamingDefault"
        SET ratingGroup = 100
        SET serviceIdentifier = "ROAM"
        EXIT

IF EXISTS serviceType
    IF serviceType == 6
        SET chargingProfile = "Forwarding"
        SET ratingGroup = 200
        SET serviceIdentifier = "FWD"
        EXIT

    IF serviceType == 10
        SET chargingProfile = "SMS"
        SET ratingGroup = 300
        SET serviceIdentifier = "MSG"
        EXIT

IF EXISTS roleOfNode
    IF roleOfNode == 0
        SET chargingProfile = "MobileOriginating"
        SET ratingGroup = 10
        SET serviceIdentifier = "MOC"
        EXIT

    IF roleOfNode == 1
        SET chargingProfile = "MobileTerminating"
        SET ratingGroup = 20
        SET serviceIdentifier = "MTC"
        EXIT

    IF roleOfNode == 2
        SET chargingProfile = "MobileForwarding"
        SET ratingGroup = 30
        SET serviceIdentifier = "CFW"
        EXIT

SET chargingProfile = "Default"
SET ratingGroup = 0
SET serviceIdentifier = "UNK"
