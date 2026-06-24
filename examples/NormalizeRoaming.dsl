FUNCTION NormalizeRoaming

INPUT
    servingMccMnc : String
    homeMccMnc : String

OUTPUT
    roamingPosition : String

RULE

IF servingMccMnc == homeMccMnc
    SET roamingPosition = "HOME"
    EXIT

SET roamingPosition = "ROAMING"
