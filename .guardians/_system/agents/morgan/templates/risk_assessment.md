# 🎯 Security Risk Assessment

**Assessment Target**: [Feature/System/Change being assessed]  
**Risk Analyst**: Morgan  
**Assessment Date**: [Current Date]  
**Assessment Type**: [New Feature | System Change | Periodic Review]  
**Overall Risk Level**: [🚨 Critical | 🔴 High | 🟠 Medium | 🟡 Low | ✅ Acceptable]

---

## 🎯 Assessment Overview

**Business Context**: [What business need this addresses]  
**Technical Scope**: [What technology/systems are involved]  
**Security Objective**: [What we're trying to protect]  
**Assessment Trigger**: [Why this assessment is being conducted]

**Key Stakeholders**:
- **Business Owner**: [Who owns the business requirement]
- **Technical Owner**: [Who's responsible for implementation]
- **Security Owner**: [Who's accountable for security]
- **Risk Owner**: [Who accepts the residual risk]

---

## 📊 Risk Context & Appetite

### Organizational Risk Appetite
- **Data Protection**: [High/Medium/Low tolerance for data risk]
- **System Availability**: [Availability risk tolerance]
- **Compliance Risk**: [Regulatory risk tolerance]
- **Reputation Risk**: [Brand damage risk tolerance]

### Asset Classification
**Primary Assets Involved**:
| Asset | Type | Classification | Business Impact |
|-------|------|----------------|----------------|
| [Customer data] | [Data] | [Confidential] | [High] |
| [Payment system] | [System] | [Critical] | [Critical] |
| [User credentials] | [Data] | [Secret] | [High] |

**Asset Owners**: [Who's responsible for each asset]  
**Asset Dependencies**: [What other systems/data this connects to]

---

## 🔍 Risk Identification

### Security Risk Categories

#### Confidentiality Risks
**RISK-C01: Unauthorized Data Access**
- **Threat**: [What could cause unauthorized access]
- **Vulnerability**: [What weakness enables this]
- **Asset**: [What data/system is at risk]
- **Impact**: [What happens if data is accessed]

**RISK-C02: Data Leakage**
- **Threat**: [Information disclosure scenarios]
- **Vulnerability**: [Technical or process weaknesses]
- **Asset**: [Affected data types]
- **Impact**: [Consequences of data exposure]

#### Integrity Risks  
**RISK-I01: Data Tampering**
- **Threat**: [Unauthorized modification scenarios]
- **Vulnerability**: [Controls that could be bypassed]
- **Asset**: [Critical data/systems]
- **Impact**: [Business consequences of data corruption]

**RISK-I02: System Compromise**
- **Threat**: [Attack methods that could succeed]
- **Vulnerability**: [System weaknesses]
- **Asset**: [Compromisable systems]
- **Impact**: [Results of system compromise]

#### Availability Risks
**RISK-A01: Service Disruption**  
- **Threat**: [DoS attacks, system failures]
- **Vulnerability**: [Single points of failure]
- **Asset**: [Critical services]
- **Impact**: [Business disruption consequences]

**RISK-A02: Performance Degradation**
- **Threat**: [Resource exhaustion attacks]
- **Vulnerability**: [Performance bottlenecks]
- **Asset**: [System performance]
- **Impact**: [User experience and business impact]

### Compliance & Regulatory Risks
**RISK-R01: Regulatory Violation**
- **Regulation**: [GDPR/PCI DSS/HIPAA/etc.]
- **Requirement**: [Specific regulatory requirement]
- **Risk**: [How requirement could be violated]
- **Penalty**: [Potential fines or sanctions]

### Third-Party & Supply Chain Risks
**RISK-T01: Vendor Security Failure**
- **Vendor**: [Third-party service provider]
- **Dependency**: [How we rely on them]
- **Risk**: [What could go wrong]
- **Impact**: [Effect on our security posture]

---

## 📈 Risk Analysis & Scoring

### Risk Assessment Matrix

| Risk ID | Risk Name | Likelihood | Impact | Risk Score | Risk Level |
|---------|-----------|------------|--------|------------|------------|
| RISK-C01 | [Unauthorized access] | [1-5] | [1-5] | [L×I] | [🚨🔴🟠🟡] |
| RISK-I01 | [Data tampering] | [1-5] | [1-5] | [L×I] | [🚨🔴🟠🟡] |
| RISK-A01 | [Service disruption] | [1-5] | [1-5] | [L×I] | [🚨🔴🟠🟡] |

### Likelihood Assessment Criteria
- **5 - Very High (Almost Certain)**: >80% chance in next 12 months
- **4 - High (Likely)**: 60-80% chance in next 12 months  
- **3 - Medium (Possible)**: 40-60% chance in next 12 months
- **2 - Low (Unlikely)**: 20-40% chance in next 12 months
- **1 - Very Low (Rare)**: <20% chance in next 12 months

### Impact Assessment Criteria
- **5 - Catastrophic**: Complete business failure, massive data breach
- **4 - Major**: Significant business disruption, major data loss
- **3 - Moderate**: Notable business impact, limited data exposure  
- **2 - Minor**: Small business impact, minimal data risk
- **1 - Insignificant**: Negligible business impact

### Risk Scoring Matrix
| Impact→ | 1-Insignificant | 2-Minor | 3-Moderate | 4-Major | 5-Catastrophic |
|---------|----------------|---------|------------|---------|----------------|
| **5-Very High** | 🟡 Medium (5) | 🟠 Medium (10) | 🔴 High (15) | 🚨 Critical (20) | 🚨 Critical (25) |
| **4-High** | 🟡 Low (4) | 🟡 Medium (8) | 🟠 Medium (12) | 🔴 High (16) | 🚨 Critical (20) |
| **3-Medium** | 🟡 Low (3) | 🟡 Low (6) | 🟡 Medium (9) | 🟠 Medium (12) | 🔴 High (15) |
| **2-Low** | 🟡 Low (2) | 🟡 Low (4) | 🟡 Low (6) | 🟡 Medium (8) | 🟠 Medium (10) |
| **1-Very Low** | ✅ Very Low (1) | 🟡 Low (2) | 🟡 Low (3) | 🟡 Low (4) | 🟡 Medium (5) |

---

## 🛡️ Existing Security Controls

### Preventive Controls
| Control | Type | Effectiveness | Coverage | Gaps |
|---------|------|---------------|----------|------|
| [Access controls] | [Identity mgmt] | [High/Med/Low] | [What's covered] | [What's missing] |
| [Input validation] | [Technical] | [Effectiveness] | [Scope] | [Limitations] |
| [Encryption] | [Crypto] | [Strength] | [Data protected] | [Unprotected data] |

### Detective Controls
| Control | Type | Detection Rate | Response Time | Gaps |
|---------|------|----------------|---------------|------|
| [SIEM alerts] | [Monitoring] | [High/Med/Low] | [X minutes] | [Blind spots] |
| [Log analysis] | [Forensic] | [Effectiveness] | [Analysis speed] | [Missing logs] |
| [Vulnerability scanning] | [Assessment] | [Coverage %] | [Scan frequency] | [Unscanned areas] |

### Responsive Controls  
| Control | Type | Activation Time | Effectiveness | Limitations |
|---------|------|-----------------|---------------|-------------|
| [Incident response] | [Process] | [X minutes] | [Success rate] | [Process gaps] |
| [Backup systems] | [Technical] | [RTO/RPO] | [Recovery rate] | [Data loss risk] |
| [Communication plan] | [Process] | [Notification time] | [Stakeholder reach] | [Communication gaps] |

---

## 🚨 High-Risk Scenarios

### Scenario 1: [Worst-Case Attack]
**Attack Path**:
```
1. [Initial compromise] → 2. [Escalation] → 3. [Lateral movement] → 4. [Data theft]
   ↓                      ↓                 ↓                     ↓
[Entry method]         [Privilege abuse]  [System hopping]      [Exfiltration]
```

**Likelihood**: [High/Medium/Low] - [Why this is likely/unlikely]  
**Business Impact**: [Specific consequences]  
**Detection Probability**: [High/Medium/Low] - [Current detection capability]  
**Response Capability**: [Effectiveness of current response]

### Scenario 2: [Insider Threat]
**Attack Path**: [How malicious insider could cause damage]  
**Likelihood**: [Assessment based on access and controls]  
**Impact**: [Damage potential from legitimate access]  
**Mitigation**: [Current insider threat controls]

### Scenario 3: [Supply Chain Compromise]
**Attack Path**: [How third-party compromise affects us]  
**Likelihood**: [Vendor security assessment]  
**Impact**: [Cascading effects on our systems]  
**Dependencies**: [Critical vendor relationships]

---

## 🔧 Risk Treatment Options

### High/Critical Risk Items (Must Address)

#### RISK-C01: [Risk Name] - Score: [XX] (🚨 Critical)
**Treatment Options**:

**Option A - Mitigate (Recommended)**:
- **Control**: [Technical control to implement]
- **Cost**: [Implementation cost]
- **Timeline**: [How long to implement]
- **Residual Risk**: [Remaining risk level]
- **Effectiveness**: [Risk reduction %]

**Option B - Transfer**:  
- **Method**: [Insurance/contract/outsource]
- **Cost**: [Transfer cost]
- **Coverage**: [What's covered]
- **Residual Risk**: [What remains]

**Option C - Avoid**:
- **Approach**: [Remove/eliminate the risk]
- **Business Impact**: [What functionality is lost]
- **Cost**: [Cost of avoidance]
- **Alternatives**: [Other ways to meet business need]

**Recommended Treatment**: [Selected option and justification]

#### RISK-I01: [Next High Risk] - Score: [XX] (🔴 High)
[Same format as above]

### Medium Risk Items (Consider Addressing)
| Risk ID | Treatment | Cost | Timeline | Priority |
|---------|-----------|------|----------|----------|
| RISK-A01 | [Mitigate with monitoring] | [$X] | [X weeks] | [1-10] |
| RISK-T01 | [Transfer via contract] | [$X] | [X days] | [1-10] |

### Low Risk Items (Accept or Monitor)
| Risk ID | Treatment | Justification | Review Date |
|---------|-----------|---------------|-------------|
| RISK-XX | Accept | [Why acceptable] | [When to reassess] |
| RISK-YY | Monitor | [What to watch for] | [Review frequency] |

---

## 💰 Cost-Benefit Analysis

### Security Investment Options
| Investment | Cost | Risk Reduction | ROI | Payback Period |
|------------|------|----------------|-----|----------------|
| [Security control 1] | [$XX] | [High/Med/Low] | [%] | [X months] |
| [Security tool 2] | [$XX] | [Risk reduction] | [%] | [X months] |
| [Process improvement] | [$XX] | [Effectiveness] | [%] | [X months] |

### Cost of Risk Materialization
- **Data Breach Cost**: [Industry average: $X per record]
- **System Downtime Cost**: [Business cost per hour]
- **Regulatory Fine Risk**: [Potential penalty amounts]
- **Reputation Damage**: [Long-term business impact]

**Total Potential Loss**: [Sum of worst-case scenarios]  
**Annual Risk Exposure**: [Expected annual loss]

---

## 🎯 Risk Treatment Plan

### Immediate Actions (0-30 days)
| Risk ID | Action Required | Owner | Cost | Due Date | Success Criteria |
|---------|-----------------|-------|------|----------|------------------|
| RISK-C01 | [Critical control implementation] | [Person] | [$] | [Date] | [Measurable outcome] |
| RISK-I01 | [High priority mitigation] | [Person] | [$] | [Date] | [Success measure] |

### Short-Term Actions (1-6 months)  
| Risk ID | Action Required | Owner | Budget | Target Date | KPI |
|---------|-----------------|-------|--------|-------------|-----|
| RISK-A01 | [Medium priority control] | [Person] | [$] | [Date] | [Metric] |
| RISK-T01 | [Process improvement] | [Person] | [$] | [Date] | [Measure] |

### Long-Term Actions (6+ months)
| Risk ID | Strategic Initiative | Owner | Budget | Timeline | Expected Outcome |
|---------|---------------------|-------|--------|----------|------------------|
| RISK-XX | [Architecture change] | [Person] | [$] | [Months] | [Strategic benefit] |

---

## 📊 Risk Monitoring & KPIs

### Key Risk Indicators (KRIs)
| Risk Area | Metric | Current | Target | Alert Threshold |
|-----------|--------|---------|--------|-----------------|
| [Data access] | [Unusual access patterns] | [Baseline] | [Goal] | [Alert level] |
| [System security] | [Vulnerability count] | [Current #] | [Target #] | [Critical threshold] |
| [Compliance] | [Control effectiveness] | [%] | [Target %] | [Minimum %] |

### Risk Dashboard Metrics
- **Total Risk Score**: [Current aggregate risk]
- **Risk Trend**: [Increasing/Stable/Decreasing]
- **Critical Risks**: [Number requiring immediate attention]
- **Overdue Mitigations**: [Number of delayed risk treatments]
- **Risk Appetite Alignment**: [Within/Exceeding acceptable levels]

---

## 🔄 Continuous Risk Management

### Regular Risk Reviews
- **Weekly**: High/Critical risk status updates
- **Monthly**: Medium risk assessment and KRI review
- **Quarterly**: Complete risk reassessment
- **Annually**: Risk appetite and methodology review

### Risk Assessment Triggers
- **New Features**: Assess security risk before deployment
- **System Changes**: Evaluate risk impact of modifications
- **Threat Intelligence**: Update risk assessment based on new threats
- **Incidents**: Reassess risk after security incidents
- **Compliance Changes**: Adjust for new regulatory requirements

---

## 🎯 Management Summary

### Executive Risk Brief
**Current Risk Posture**: [Overall security risk level]  
**Key Business Risks**: [Top risks that could affect business objectives]  
**Investment Priorities**: [Where to spend security budget]  
**Risk Appetite Alignment**: [Are we within acceptable risk levels?]

### Decision Points for Management
1. **Risk Tolerance**: [Are current risk levels acceptable?]
2. **Investment Level**: [How much to invest in risk reduction?]
3. **Risk Transfer**: [What risks to transfer via insurance/contracts?]
4. **Risk Acceptance**: [What residual risks to formally accept?]

### Morgan's Risk Assessment
*"[Direct, honest assessment of the risk landscape and recommended actions]"*

**Bottom Line**: [Simple statement of whether this should proceed and under what conditions]

---

## 📋 Risk Register Entry

**Risk ID**: [RISK-YYYY-XXX]  
**Risk Owner**: [Person accountable for the risk]  
**Current Risk Score**: [Number] ([Level])  
**Target Risk Score**: [Number] ([Level])  
**Review Date**: [When to reassess]  
**Status**: [Open/In Progress/Closed]

---

**Risk Assessment By**: Morgan (Security Specialist)  
**Next Review Date**: [When to update this assessment]  
**Distribution**: [Who should receive this assessment]

---

*Morgan's Risk Reality: Risk assessment isn't about eliminating all risks - that's impossible and would stop all business progress. It's about understanding what we're getting into and making sure we're prepared for what could go wrong. These aren't theoretical risks - they're based on real attack patterns I've seen succeed against similar systems.*