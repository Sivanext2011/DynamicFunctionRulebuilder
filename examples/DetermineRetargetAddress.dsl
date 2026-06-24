FUNCTION DetermineRetargetAddress

INPUT
    ResultCode : LongNumber
    CoreAnnouncementCode : LongNumber

OUTPUT
    RetargetAddress : String

RULE

IF ResultCode == 4012
    IF CoreAnnouncementCode == 1934
        SET RetargetAddress = "8321"
        EXIT

SET RetargetAddress = "8342"
