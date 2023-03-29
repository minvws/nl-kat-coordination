## Services
```mermaid

graph TD

	  A(["Boefjes \n (Capture raw data)"])
	  B(["Bytes \n (Store raw data)"])
    C(["Normalizers \n (Structure raw data)"])
    D["Octopoes \n (Store entities)"]
    E(["Scheduler \n (Schedule new Boefjes)"])
    F[(XTDB)]

	  A --> B
    B --> C
    C --> D
    D --> E
    E --> A
    D --> F

    classDef highlight fill:#ca005d,color:white,stroke:#333,stroke-width:2px;
    classDef processor fill:#eee,stroke:#333,stroke-width:2px;
    class D,F highlight
    class A,B,C,E processor

```

## Dataflow
```mermaid
graph LR

	  A(["Boefjes"])
    B(["Normalizer"])
    C["Octopoes"]
    D[(XTDB)]

    A -- Raw Data --> B
    B -- Structured Data --> C
    C -- Entities --> D

```

## OWA vs CWA
```mermaid
graph LR

    subgraph all ["All knowledge"]
        C["..."]
        D["..."]
        C --- D
        subgraph kat ["KAT's knowledge"]
            direction LR
            A("IPv4 \n1.1.1.1")
            B("Port 80 \nOpen")

            A --- B
        end
    end
```

## System that tracks orders
```mermaid
graph LR
    subgraph db ["DB Table"]
      direction LR
      A("Order 1")
      B("Order 2")
      C("...")
      D("Order 30")
      
      Orders --- A
      Orders --- B
      Orders --- C
      Orders --- D
    end
```

## Simple rule

```mermaid
flowchart LR

  subgraph kb [knowledge base]
    A("IPv4\n1.1.1.1")
    B("Port 3306\nOpen")
    
    A --- B
  end
  
  subgraph dk [derived knowledge]
    C("IPv4\n1.1.1.1")
    D("Port 3306\nOpen")
    E("Vulnerability\nSeverity: high")
    
    C --- D --- E
  end
  
  kb --> rules --> dk
  
  classDef base fill:#eee,stroke:#333,stroke-width:2px;
  classDef derived fill:#ca005d,color:white,stroke:#333,stroke-width:2px;
  class A,B,C,D base
  class E derived
```

## Logic chaining
```mermaid
flowchart LR

    A(["Fact A"])
    B(["Fact B"])
    C(["Fact C"])
    D(["Fact D"])
    
    C1["Conclusion 1"]
    C2["Conclusion 2"]
    C3["Conclusion 3"]
    
    O1(("AND"))
    O2(("OR"))
    O3(("AND"))
    
    A --> O1 --> C1 --> O3 --> C3
    B --> O1
    
    C --> O2 --> C2 --> O3
    D --> O2
    
    classDef fact fill:#ca005d,stroke:#333,color:white,stroke-width:2px;
    classDef conclusion fill:#154273,stroke:#333,color:white,stroke-width:2px;
    classDef operator fill:#eee,stroke:#333,stroke-width:2px;
    class A,B,C,D fact
    class C1,C2,C3 conclusion
    class O1,O2,O3 operator
    
```


## Knowledge base, rules and derived knowledge
```mermaid

flowchart LR
    
    subgraph kb [knowledge base]
        a1("a")
        b1("b")
        c1("c")
        d1("d")
        
        a1 --- b1
        a1 --- c1
        c1 --- d1
    end
   
   subgraph dk [derived knowledge]
        a2("a")
        b2("b")
        c2("c")
        d2("d")
        e2("e")
        f2("f")
        g2("g")
        
        a2 --- b2
        a2 --- c2
        c2 --- d2
        a2 --- e2
        d2 --- f2
        c2 --- g2
    end
    
    kb --> rules --> dk
   
    classDef base fill:#eee,stroke:#333,stroke-width:2px;
    classDef derived fill:#ca005d,color:white,stroke:#333,stroke-width:2px;
    class a1,b1,c1,d1,a2,b2,c2,d2 base
    class e2,f2,g2 derived
```

```mermaid  
graph
 

    A[Raw data]
    B[ClaimSpace]
    C[FactSpace]
    D[Materialized Knowledge Graph]
    
    p1["entity extraction \n(whiskers)"]
    p2["entity recognition \n(model)"]
    p3["conflict resolution"]
    p4["inference \n(bits)"]
    
    A --> p1 
    p1 --> p2 --> B --> p3 --> C --> p4 --> D
    p4 -.-> B
    p4 -.-> C
    
    classDef stage fill:#ca005d,color:white,stroke:#333,stroke-width:2px;  
    classDef processor fill:#eee,stroke:#333,stroke-width:2px;
    class A,B,C,D stage
    class p1,p2,p3,p4 processor
```

## ClaimSpace

```mermaid
flowchart LR

    A["PluginOutput\nNmap on IPv4 1.1.1.1"]
    
    subgraph ClaimSet
        direction TB
        B["Claim:\nIPv4 1.1.1.1 exists"]
        C["Claim:\nPort 80 of IPv4 1.1.1.1 exists"]
        D["Claim:\nState of Port 80 of IPv4 1.1.1.1 = open"]

        B ~~~ C ~~~ D
    end
    
    A --- ClaimSet
```

## Factspace
The stage where claims are consolidated into (assumed) facts.

```mermaid

graph LR
    
    subgraph ClaimSpace
        A["Claim:\nIPv4 1.1.1.1 does not exist\nSource: Shodan\nTimestamp: 1 day ago"]
        B["Claim:\nIPv4 1.1.1.1 exists\nSource: HTTPRequest\nTimestamp: 1 hour ago"]
        C["Claim:\nPort 80 of IPv4 exists\nSource: HTTPRequest\nTimestamp: 1 hour ago"]
        D["Claim:\nState of Port 80 of IPv4 1.1.1.1 = open\nSource: HTTPRequest\nTimestamp: 1 hour ago"]
    end
    
    E(("IPv4\n1.1.1.1"))
    F(("Port\n1.1.1.1:80\nState: open"))
    
    A -- confidence: 0.4 --- E
    B -- confidence: 0.8 --- E
    C -- confidence: 0.9 --- F
    D -- condifence: 0.85 --- F
    
```
