import { WS_URL } from "../constants";
import type { MessageEnvelope, SubscriptionHandlers } from "./eventBus";
import eventBus from "./eventBus";

const ws = new WebSocket(WS_URL);

ws.onopen = () => {
    console.log("WebSocket connected");
};

ws.onmessage = (messageEvent: MessageEvent) => {
    try {
        const envelope: MessageEnvelope = JSON.parse(messageEvent.data);
        // console.log('Received envelope:', envelope);

        eventBus.publish(envelope.topic, envelope.payload);

        // If a subtopic is provided, construct a compound topic and publish there as well.
        if (envelope.subtopic) {
            const compoundTopic = `${ envelope.topic }.${ envelope.subtopic }`;
            eventBus.publish(compoundTopic, envelope.payload);
        }
    } catch (error) {
        console.error('Error processing message envelope:', error);
    }
};


ws.onerror = (error) => {
    console.error("WebSocket error:", error);
};

ws.onclose = () => {
    console.log("WebSocket closed");
};


// Keep track of the base topics already subscribed to (for server notifications)
const activeBaseTopics = new Set<string>();

/**
 * Subscribes to a single topic with optional subtopic handlers.
 *
 * @param topic - The base topic (e.g. a device serial).
 * @param handlers - An object containing a base handler and/or subtopic handlers.
 */
export const subscribe = <T extends Record<string, any>>(
    topic: string,
    handlers: SubscriptionHandlers<T>
) => {
    // Subscribe to the base topic if a base handler is provided.
    if (handlers.base) {
        eventBus.subscribe(topic, handlers.base);
    }
    // For each subtopic provided, subscribe to the compound topic.
    if (handlers.subtopics) {
        // We assert that Object.entries returns an array of [key, handler] pairs.
        (Object.entries(handlers.subtopics) as [keyof T, any][]).forEach(([subtopic, handler]) => {
            const compoundTopic = `${ topic }.${ String(subtopic) }`;
            eventBus.subscribe(compoundTopic, handler);
        });
    }
    // Only send a subscription to the server for the base topic if we haven't already.
    if (!activeBaseTopics.has(topic)) {
        activeBaseTopics.add(topic);
        ws.send(JSON.stringify({ subscribe: [topic] }));
    }
};

/**
 * Unsubscribes the given handlers from a single topic and its subtopics.
 *
 * @param topic - The base topic.
 * @param handlers - The handlers previously registered.
 */
export const unsubscribe = <T extends Record<string, any>>(
    topic: string,
    handlers: SubscriptionHandlers<T>
) => {
    if (handlers.base) {
        eventBus.unsubscribe(topic, handlers.base);
    }
    if (handlers.subtopics) {
        (Object.entries(handlers.subtopics) as [keyof T, any][]).forEach(([subtopic, handler]) => {
            const compoundTopic = `${ topic }.${ String(subtopic) }`;
            eventBus.unsubscribe(compoundTopic, handler);
        });
    }
    if (activeBaseTopics.has(topic)) {
        activeBaseTopics.delete(topic);
        ws.send(JSON.stringify({ unsubscribe: [topic] }));
    }
};

export default ws;
