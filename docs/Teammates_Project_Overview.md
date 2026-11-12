# Project #9: SDN-Integrated TCP Pub-Sub Messaging System
## Beginner-Friendly Project Overview & Team Guide

---

### 1. What Is Our Project? (The "Private YouTube" Analogy)

Think of our project as a **private mini-YouTube notification system** running inside a private computer network:

* **Content Creators (Publishers):** In YouTube, creators upload videos to specific channels. In our project, these are programs (`publisher.py`) pushing updates to specific topics (like `alerts/emergency` or `sensors/temperature`).
* **Subscribers (Viewers):** In YouTube, you hit "Subscribe" and turn on notifications for specific channels so you only get alerts for what you care about. In our code, these are programs (`subscriber.py`) listening for specific topics.
* **The Platform (The Broker):** YouTube doesn't force creators to send video notifications directly from their personal laptops to millions of phones. YouTube acts as the middleman. In our project, that middleman is the **Broker** (`broker.py`). The publishers send messages to the Broker, and the Broker instantly routes them to whoever subscribed to that topic.

---

### 2. Why Does It Need "SDN" (Software-Defined Networking)?

In a regular home or office network, all internet traffic gets dumped onto whatever cable or Wi-Fi router is available. If someone starts downloading a huge file, your game lags or critical messages get delayed.

In our project, we add an **SDN Controller** (the network "traffic cop"):

1. **VIP Express Lane vs. Regular Road:** Our virtual network has two routes between the switches:
   * **Fast Lane (`s1 -> s2 -> s4`):** Super fast (2ms delay, 20 Mbps bandwidth).
   * **Slow / Default Lane (`s1 -> s3 -> s4`):** Slower (25ms delay, 5 Mbps bandwidth).
2. **Topic Prioritization:** The SDN controller looks at the port number on the packets. If a message is marked as critical/emergency (`Port 5001`), the controller automatically forces it through the **Fast Lane**. Standard messages (`Port 5002`) travel along the normal route.
3. **Smart Detours (Robustness & Failover):** If someone cuts the fast cable (e.g., we type `link s1 s2 down` in Mininet), the SDN controller immediately spots the break and moves all traffic to the backup route in milliseconds without dropping the connection.
4. **App-to-Network Communication:** If a regular channel suddenly gets spammed with a ton of urgent messages, the Broker pings the SDN controller via a REST API: *"Hey, this channel is blowing up, give it the Fast Lane!"*—and the network dynamically adjusts on the fly.

---

### 3. How the 3 of Us Divide the Work

| Teammate | What You Actually Build | What You Tell the Evaluator During Viva |
| :--- | :--- | :--- |
| **Member 1 (Socket Lead)** | Writes the Python TCP programs (`broker.py`, `publisher.py`, `subscriber.py`, `protocol.py`). | *"I handled the application layer. I built a multi-threaded TCP broker that handles dynamic subscriptions, enforces reliable message delivery, and prevents packet corruption using length-prefixed framing."* |
| **Member 2 (SDN Lead)** | Builds the network topology in Mininet (`pubsub_topo.py`) and writes the OpenFlow switch controller (`sdn_controller.py`). | *"I built the programmable network layer. I created the 4-switch diamond topology and wrote the SDN controller that classifies packets by port and manages fast/slow routes and loop-free switching."* |
| **Member 3 (Integration & Testing Lead)** | Connects the Broker to the SDN Controller via REST API, runs the stress/breakage tests, and plots the graphs (`plot_metrics.py`). | *"I handled end-to-end integration and evaluation. I made the Broker trigger dynamic SDN reroutes during traffic spikes, simulated link failures and congestion, and generated the latency comparison graphs."* |

---

### 4. What Does the Final Demo Look Like?

During evaluation, we open two or three terminal windows and show the teachers four simple steps:

1. **Start the Controller & Mininet:** Show the 4-switch diamond topology connecting cleanly.
2. **Start the Broker & Subscribers:** Subscriber A listens to emergency alerts; Subscriber B listens to sensor data.
3. **Send Messages & Show Latency Difference:** Show that emergency messages arrive in **~6ms** (Fast Path) while normal messages take **~55ms** (Slow Path).
4. **The "Boom" Moment (Challenging Scenario):** We cut the fast link live in front of the teacher (`link s1 s2 down`). The controller logs the break, reroutes the packets to the backup path instantly, and the subscriber keeps receiving messages without crashing.