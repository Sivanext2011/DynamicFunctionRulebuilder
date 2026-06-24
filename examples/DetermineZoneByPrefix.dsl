FUNCTION DetermineZoneByPrefix

INPUT
    calledPartyNumber : String

OUTPUT
    zone : String

INTERNAL
    prefix : String

RULE

IF EXISTS calledPartyNumber
    IF LOOKUP table="rmref://coba/globalListSpecification/NumberRangesMapping/globalList/ZoneLookup" column="prefix" key=prefix search=EXACT_MATCH
        SET zone = "LocalZone"
        EXIT

SET zone = "DefaultZone"
