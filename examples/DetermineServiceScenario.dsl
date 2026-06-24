FUNCTION DetermineServiceScenario

INPUT
    serviceType : LongNumber
    roleOfNode : IntegerNumber

OUTPUT
    serviceScenario : String

RULE

IF serviceType == 6
    SET serviceScenario = "Forwarding"
    EXIT

IF roleOfNode == 0
    SET serviceScenario = "MobileOriginating"
    EXIT

IF roleOfNode == 1
    SET serviceScenario = "MobileTerminating"
    EXIT
