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
6. Conditions use: "is", "equals", "is not", "is present", "is not present"
7. Multiple conditions on same line use: "and"
8. Actions use: "then set <target> to <value>"
9. Exit after a rule: append "and exit"
10. Default/fallback: "Default set <target> to <value>"
11. Concatenation: "Concatenate <source> and <addString> into <target>" (ONLY 2 inputs per step)
12. COBA table lookup: "Lookup <keyParam> in table <TableName> column <columnName>, set <resultColumn> to <target>"

PARAMETER NAMING:
- Parameter names can contain letters, digits, underscores, hyphens, and dots
- Examples: Ericsson-Location-MCC-MNC, plmnId.mcc, serviceType, Result-Code
- Use the EXACT parameter names as they appear in CHA specification

AVAILABLE DATA TYPES:
- String, IntegerNumber, LongNumber, Boolean
- StringList, IntegerNumberList, LongNumberList
- OctetString, DateTime, Measurement
- Enumerated, AddressString, AddressStringList

AVAILABLE CONDITION PATTERNS:
- "If <variable> is <value> then ..."
- "If <variable> equals <value> then ..."
- "If <variable> is not <value> then ..."
- "If <var1> is <val1> and <var2> is <val2> then ..."
- "If <variable> is present" (existence check)
- "If <variable> is not present" (non-existence check)

AVAILABLE ACTION PATTERNS:
- "set <target> to <value>"
- "set <target> to <value> and exit"
- "Concatenate <source> and <addString> into <target>" (appends addString to source, stores in target)
- "Lookup <keyParam> in table <TableName> column <columnName>, set <resultColumn> to <target>"

IMPORTANT - CONCATENATION RULES:
The CHA AddStringModifier takes ONLY 2 inputs per operation (source + addString → target).
To join multiple parts (e.g., MCC + "-" + MNC), use multiple steps:
  "Set LocationMCCMNC to Mcc"
  "Concatenate LocationMCCMNC and '-' into LocationMCCMNC"
  "Concatenate LocationMCCMNC and Mnc into LocationMCCMNC"
Each step appends ONE value to the existing string. Never put 3+ sources in one concatenate.

FOR OTHER COMPLEX OPERATIONS:
- COBA table lookup (set value from table):
  "Lookup <keyParam> in table <TableName> column <columnName>, set <resultColumn> to <target>"
  Where:
    - TableName = the globalListSpecification name in CHA (e.g. GL_MccMncToZone_data)
    - keyParam = the input/internal parameter holding the lookup key
    - columnName = the column in the COBA table to search
    - resultColumn = the column to return the value from
    - target = the output parameter to store the result
  The tool will form the URI: rmref://coba/globalListSpecification/{TableName}/globalList/{TableName}
  For multiple result columns from same table, write one Lookup line per result column.

- Split: "Split <source> by '<delimiter>' into <target>"
- Substring: "Extract substring of <source> from <start> to <end> into <target>"
- Convert: "Convert <source> to <target>"

ENUMERATED TYPES:
- Always use numeric values in conditions (0, 1, 2...), NOT string labels
- Example: "If roamerInOut is 0" not "If roamerInOut is Inroam"

OUTPUT FORMAT EXAMPLE:
---
Function: DetermineServiceScenario

Input: serviceType (LongNumber), roleOfNode (IntegerNumber)
Output: serviceScenario (String)

If serviceType is 6 then set serviceScenario to Forwarding and exit
If roleOfNode is 0 then set serviceScenario to MobileOriginating and exit
If roleOfNode is 1 then set serviceScenario to MobileTerminating and exit
Default set serviceScenario to Unknown
---

EXAMPLE WITH CONCAT AND LOOKUP:
---
Function: DetermineRoamingZone

Input: Mcc (String), Mnc (String)
Output: LocationMCCMNC (String), roamingZone (String)

Set roamingZone to Unknown
Set LocationMCCMNC to Mcc
Concatenate LocationMCCMNC and '-' into LocationMCCMNC
Concatenate LocationMCCMNC and Mnc into LocationMCCMNC
Lookup LocationMCCMNC in table GL_MccMncToZone_data column MCCMNC, set ZoneGroup to roamingZone
Exit
---

IMPORTANT: Output ONLY the function definition text. No explanations, no markdown, no code blocks.

MY REQUIREMENT:
[Describe your requirement here]
```

---

## EXAMPLE PROMPTS

### Example 1: Simple routing logic

```
MY REQUIREMENT:
I need a function that takes Result-Code (LongNumber) and Announcement-Code (LongNumber) as input,
and outputs a Retarget-Address (String).
If result code is 4012 and announcement code is 1934, retarget to "8321".
Otherwise retarget to "8342".
```

Expected output:
```
Function: DetermineRetargetAddress

Input: Result-Code (LongNumber), Announcement-Code (LongNumber)
Output: Retarget-Address (String)

If Result-Code is 4012 and Announcement-Code is 1934 then set Retarget-Address to 8321 and exit
Default set Retarget-Address to 8342
```

---

### Example 2: Concatenation with literal separator (2 steps)

```
MY REQUIREMENT:
I have Mcc (String) and Mnc (String) as inputs.
Output is LocationMCCMNC (String).
Concatenate Mcc, a hyphen, and Mnc together into LocationMCCMNC.
```

Expected output:
```
Function: DetermineLocationMccMnc

Input: Mcc (String), Mnc (String)
Output: LocationMCCMNC (String)

Set LocationMCCMNC to Mcc
Concatenate LocationMCCMNC and '-' into LocationMCCMNC
Concatenate LocationMCCMNC and Mnc into LocationMCCMNC
Exit
```

---

### Example 3: COBA table lookup with default

```
MY REQUIREMENT:
Input is LocationMCCMNC (String).
Outputs are roamingCountry (String) and roamingZone (String).
Lookup LocationMCCMNC in global list GL_MccMncToZone_data, 
search column MCCMNC with exact match.
Set the Country column value to roamingCountry.
Set the ZoneGroup column value to roamingZone.
Default both to "Unknown" if no match.
```

Expected output:
```
Function: DetermineRoamingCountryZone

Input: LocationMCCMNC (String)
Output: roamingCountry (String), roamingZone (String)

Set roamingCountry to Unknown
Set roamingZone to Unknown
Lookup LocationMCCMNC in table GL_MccMncToZone_data column MCCMNC, set Country to roamingCountry
Lookup LocationMCCMNC in table GL_MccMncToZone_data column MCCMNC, set ZoneGroup to roamingZone
Exit
```

---

### Example 4: RAT Type mapping

```
MY REQUIREMENT:
Map Radio Access Technology integer code to a readable string.
Input is ratType (IntegerNumber), output is networkType (String).
1=UTRAN, 2=GERAN, 3=WLAN, 6=EUTRAN, 8=NR, 9=EUTRA-NR.
Default to UNKNOWN.
```

Expected output:
```
Function: MapRATType

Input: ratType (IntegerNumber)
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

### Example 5: Existence check with multiple actions

```
MY REQUIREMENT:
Input: anncid (LongNumber), Result-Code (LongNumber)
Output: resultCode (LongNumber)
If anncid is present and anncid is 6705 then set resultCode to 4800 and exit.
If Result-Code is present then set resultCode to Result-Code and exit.
Default resultCode to 0.
```

Expected output:
```
Function: DetermineResultCode

Input: anncid (LongNumber), Result-Code (LongNumber)
Output: resultCode (LongNumber)

If anncid is present and anncid is 6705 then set resultCode to 4800 and exit
If Result-Code is present then set resultCode to Result-Code and exit
Default set resultCode to 0
```

---

### Example 6: Multi-output with same lookup

```
MY REQUIREMENT:
Input: MSISDN (String)
Outputs: customerSegment (String), billingCategory (String), priorityLevel (IntegerNumber)
Lookup MSISDN in table GL_CustomerProfile column MSISDN.
Set Segment column to customerSegment, Category to billingCategory, Priority to priorityLevel.
Default: customerSegment=Standard, billingCategory=Postpaid, priorityLevel=0
```

Expected output:
```
Function: DetermineCustomerProfile

Input: MSISDN (String)
Output: customerSegment (String), billingCategory (String), priorityLevel (IntegerNumber)

Set customerSegment to Standard
Set billingCategory to Postpaid
Set priorityLevel to 0
Lookup MSISDN in table GL_CustomerProfile column MSISDN, set Segment to customerSegment
Lookup MSISDN in table GL_CustomerProfile column MSISDN, set Category to billingCategory
Lookup MSISDN in table GL_CustomerProfile column MSISDN, set Priority to priorityLevel
Exit
```

---

## TIPS FOR BEST RESULTS

1. **Use exact CHA parameter names** - including hyphens and dots (e.g., `Ericsson-Location-MCC-MNC`, `plmnId.mcc`)
2. **Use correct CHA data types** - `IntegerNumber` not `Integer`, `LongNumber` not `Long`
3. **Concatenation is 2 inputs only** - use multiple steps to join 3+ parts (set first, then append each)
4. **Numeric values don't need quotes** - just write the number
5. **String values** - the tool auto-quotes them, no need to add quotes yourself
6. **One rule per line** - don't combine multiple rules on one line
7. **Always include a default** - prevents undefined output in CHA
8. **Exit after definitive matches** - prevents fallthrough to later rules
9. **For COBA lookups** - one Lookup line per result column from the table
10. **Enumerated types use integers** - conditions compare numeric values (0, 1, 2...), not string labels

---

## DSL QUICK REFERENCE

The tool converts English text to this DSL format:

```
FUNCTION <Name>

INPUT
    <param> : <DataType>

OUTPUT
    <param> : <DataType>

INTERNAL
    <param> : <DataType>

RULE

SET <target> = "<value>"
SET LocationMCCMNC = Mcc
CONCAT LocationMCCMNC, "-" INTO LocationMCCMNC
CONCAT LocationMCCMNC, Mnc INTO LocationMCCMNC
LOOKUP_SET table="rmref://coba/globalListSpecification/<Table>/globalList/<Table>" column="<col>" key=<param> result="<resultCol>" target=<targetParam> search=EXACT_MATCH
IF <var> == <value>
    SET <target> = "<value>"
    EXIT
IF EXISTS <var>
    SET <target> = <var>
EXIT
```

Paste the generated English text into the CHA Compiler web tool or save as .txt file and run:
```
python cha_compile.py english my_rules.txt --compile -o output.zip
```
