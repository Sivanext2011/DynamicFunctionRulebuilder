# GenAI Prompt Template for CHA Dynamic Function Generator

Use this prompt with any GenAI (ChatGPT, Claude, Gemini, Copilot, etc.) to generate
text that can be directly pasted into the CHA Dynamic Function Compiler tool.

---

## PROMPT TEMPLATE (Copy and customize)

```
You are a telecom charging engineer writing Ericsson CHA Dynamic Function rules.

Generate the rule definition in the EXACT format below for my requirement.

FORMAT RULES:
1. First line: "Function: <FunctionName>" (no spaces in name, use CamelCase)
2. Parameters section: "Input: <name> (<type>), <name2> (<type>)" on one line
3. Output section: "Output: <name> (<type>)"  
4. Internal section (if needed): "Internal: <name> (<type>)"
5. Rules: One rule per line starting with "If"
6. Conditions use: "is", "equals", "is not"
7. Multiple conditions on same line use: "and"
8. Actions use: "then set <target> to <value>"
9. Exit after a rule: append "and exit"
10. Default/fallback: "Default set <target> to <value>"

AVAILABLE DATA TYPES:
- String, Integer, Long, Boolean
- StringList, OctetString, DateTime, Measurement

AVAILABLE CONDITION PATTERNS:
- "If <variable> is <value> then ..."
- "If <variable> equals <value> then ..."
- "If <variable> is not <value> then ..."
- "If <var1> is <val1> and <var2> is <val2> then ..."
- "If <variable> is present" (existence check)

AVAILABLE ACTION PATTERNS:
- "set <target> to <value>"
- "set <target> to <value> and exit"

FOR COMPLEX OPERATIONS (will appear as comments in DSL, configure manually in CHA):
- "Decode the <AVP>" (ConvertDataTypeModifier)
- "Split <source> by <delimiter>" (SplitStringModifier)
- "Extract the <field>" (SubstringModifier)
- "Combine <x> and <y> to form <z>" (ConcatenateModifier)
- For COBA table lookups use EXACTLY this format:
  "Check against table <TableName> using <keyParam> column <columnName>"
  Where:
    - TableName = the globalListSpecification name in CHA (e.g. MapMCCMNCToZone)
    - keyParam = the internal/input parameter holding the lookup key value (e.g. tmpMCC)
    - columnName = the column in the COBA table to search (e.g. MCCMNC)
  The tool will form the URI: rmref://coba/globalListSpecification/{TableName}/globalList/{TableName}
  Users can override the exact URI via the COBA form in the web tool.

OUTPUT FORMAT EXAMPLE:
---
Function: DetermineServiceScenario

Input: serviceType (Long), roleOfNode (Integer)
Output: serviceScenario (String)

If serviceType is 6 then set serviceScenario to Forwarding and exit
If roleOfNode is 0 then set serviceScenario to MobileOriginating and exit
If roleOfNode is 1 then set serviceScenario to MobileTerminating and exit
Default set serviceScenario to Unknown
---

MY REQUIREMENT:
[Describe your requirement here]
```

---

## EXAMPLE PROMPTS

### Example 1: Simple routing logic

```
MY REQUIREMENT:
I need a function that takes Result-Code (Long) and Announcement-Code (Long) as input,
and outputs a Retarget-Address (String).
If result code is 4012 and announcement code is 1934, retarget to "8321".
Otherwise retarget to "8342".
```

Expected output:
```
Function: DetermineRetargetAddress

Input: ResultCode (Long), AnnouncementCode (Long)
Output: RetargetAddress (String)

If ResultCode is 4012 and AnnouncementCode is 1934 then set RetargetAddress to 8321 and exit
Default set RetargetAddress to 8342
```

---

### Example 2: RAT Type mapping

```
MY REQUIREMENT:
Map Radio Access Technology integer code to a readable string.
Input is ratType (Integer), output is networkType (String).
1=UTRAN, 2=GERAN, 3=WLAN, 6=EUTRAN, 8=NR, 9=EUTRA-NR.
Default to UNKNOWN.
```

Expected output:
```
Function: MapRATType

Input: ratType (Integer)
Output: networkType (String)

If ratType is 1 then set networkType to UTRAN and exit
If ratType is 2 then set networkType to GERAN and exit
If ratType is 3 then set networkType to WLAN and exit
If ratType is 6 then set networkType to EUTRAN and exit
If ratType is 8 then set networkType to NR and exit
If ratType is 9 then set networkType to EUTRA-NR and exit
Default set networkType to UNKNOWN
```

---

### Example 3: Roaming determination

```
MY REQUIREMENT:
Determine roaming position. Takes servingMccMnc and homeMccMnc as String inputs.
Output roamingPosition as String.
If serving equals home, position is HOME. Otherwise ROAMING.
```

Expected output:
```
Function: DetermineRoamingPosition

Input: servingMccMnc (String), homeMccMnc (String)
Output: roamingPosition (String)

If servingMccMnc equals homeMccMnc then set roamingPosition to HOME and exit
Default set roamingPosition to ROAMING
```

---

### Example 4: Complex function with COBA lookup

```
MY REQUIREMENT:
Extract MCC/MNC from Access-Network-Information (OctetString) and determine
subscriber location using COBA table lookup.
If the AVP exists, decode it, extract MCC and MNC, combine into PLMN,
then lookup the TAC in table TACLocationMapping.
If match found, set subscriberLocation from the table.
If no AVP present, set subscriberLocation to "Not Available".
Default subscriberLocation is "Unknown".
```

Expected output:
```
Function: DetermineSubscriberLocation

Input: accessNetworkInfo (OctetString)
Output: subscriberLocation (String)
Internal: tmpDecoded (String), tmpMCC (String), tmpMNC (String), tmpTAC (String), tmpPLMN (String)

Set subscriberLocation to Not Available

If accessNetworkInfo is present
    Decode the accessNetworkInfo AVP
    Extract the MCC
    Extract the MNC
    Extract the TAC
    Combine MCC and MNC to form a PLMN value
    Set subscriberLocation to Unknown
    Check against table TACLocationMapping using tmpTAC column TAC
    If a matching TAC is found:
        Set subscriberLocation to Matched and exit
```

---

### Example 5: Multi-output charging profile

```
MY REQUIREMENT:
Determine charging profile based on service type and role of node.
Inputs: serviceType (Long), roleOfNode (Integer), isRoaming (Boolean)
Outputs: chargingProfile (String), ratingGroup (Integer), serviceId (String)

If roaming=1: profile=RoamingDefault, ratingGroup=100, serviceId=ROAM
If serviceType=6: profile=Forwarding, ratingGroup=200, serviceId=FWD  
If serviceType=10: profile=SMS, ratingGroup=300, serviceId=MSG
If roleOfNode=0: profile=MOC, ratingGroup=10, serviceId=MOC
If roleOfNode=1: profile=MTC, ratingGroup=20, serviceId=MTC
Default: profile=Default, ratingGroup=0, serviceId=UNK
```

Expected output:
```
Function: DetermineChargingProfile

Input: serviceType (Long), roleOfNode (Integer), isRoaming (Boolean)
Output: chargingProfile (String), ratingGroup (Integer), serviceId (String)

If isRoaming is 1 then set chargingProfile to RoamingDefault and exit
If serviceType is 6 then set chargingProfile to Forwarding and exit
If serviceType is 10 then set chargingProfile to SMS and exit
If roleOfNode is 0 then set chargingProfile to MOC and exit
If roleOfNode is 1 then set chargingProfile to MTC and exit
Default set chargingProfile to Default
```

Note: For multi-output, the tool currently sets one output per IF line.
For multiple outputs in same branch, write multiple IF blocks with same condition,
or manually edit the generated DSL to add multiple SET statements.

---

## TIPS FOR BEST RESULTS

1. **Keep parameter names simple** - no spaces, use CamelCase (e.g., `ResultCode` not `result code`)
2. **Use hyphens in names** - they'll be auto-removed (e.g., `Result-Code` becomes `ResultCode`)
3. **Numeric values don't need quotes** - just write the number
4. **String values** - the tool auto-quotes them, no need to add quotes yourself
5. **One rule per line** - don't combine multiple rules on one line
6. **Always include a default** - prevents undefined output in CHA
7. **Exit after definitive matches** - prevents fallthrough to later rules
8. **For COBA lookups** - specify: table name, key parameter, column name

---

## QUICK REFERENCE CARD

```
Function: <Name>

Input: <param> (<type>), <param2> (<type>)
Output: <param> (<type>)
Internal: <param> (<type>)

If <var> is <value> then set <target> to <result> and exit
If <var1> is <val1> and <var2> is <val2> then set <target> to <result> and exit
Default set <target> to <fallback>
```

Paste the generated text into the CHA Compiler web tool or save as .txt file and run:
```
python cha_compile.py english my_rules.txt --compile -o output.zip
```
