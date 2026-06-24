FUNCTION DetermineSubscriberLocation

INPUT
    UserLocationInfo : OctetString
    SgsnMccMnc : String

OUTPUT
    subscriberLocation : String

INTERNAL
    tmpLocationString : String
    tmpLocationParts : String
    tmpMCC : String
    tmpMNC : String
    tmpTAC : String
    tmpPLMN : String

RULE

SET subscriberLocation = "Not Available"

IF EXISTS UserLocationInfo
    SET subscriberLocation = "Unknown"
    IF LOOKUP table="rmref://coba/globalListSpecification/TACLocationMapping/globalList/TACLocationMapping" column="TAC" key=tmpTAC search=EXACT_MATCH
        SET subscriberLocation = "Matched"
        EXIT
