//eventBus.ts

/**
 * A generic message envelope for use with an event bus or any pub/sub system.
*
* @template T - The type of the payload.
*/
export interface MessageEnvelope<T = any> {
    topic: string;
    subtopic?: string;
    payload: T;
    timestamp?: number;
}


// A generic event handler type: it receives a payload of type T.
export type EventHandler<T = any> = (payload: T) => void;


/**
 * Subscriptions defines the callbacks for a given topic.
 *
 * - The `base` handler will receive any payload from the union of all subtopic payloads.
 * - The `subtopics` property is a mapping where each key corresponds to a subtopic
 *   and its value is a callback that is specifically typed for that subtopic.
 */
export interface SubscriptionHandlers<PayloadMapping extends Record<string, any>> {
    base?: EventHandler<PayloadMapping[keyof PayloadMapping]>;
    subtopics?: { [K in keyof PayloadMapping]?: EventHandler<PayloadMapping[K]> };
}

/**
 * EventBus is a simple publish/subscribe (pub/sub) system that uses the terms
 * "topic" to identify channels. Components can subscribe to a topic to receive
 * payloads published on that topic.
 */
export class EventBus {
    // A Map where the keys are topic strings and the values are sets of handlers.
    private topics: Map<string, Set<EventHandler<any>>> = new Map();

    /**
     * Subscribe to a topic with a handler.
     * @param topic - The topic (or subject) to subscribe to.
     * @param handler - The function that will be called with payloads published to this topic.
     */
    subscribe<T>(topic: string, handler: EventHandler<T>): void {
        if (!this.topics.has(topic)) {
            this.topics.set(topic, new Set());
        }
        this.topics.get(topic)!.add(handler as EventHandler<any>);
    }

    /**
     * Unsubscribe a handler from a topic.
     * @param topic - The topic to unsubscribe from.
     * @param handler - The handler function to remove.
     */
    unsubscribe<T>(topic: string, handler: EventHandler<T>): void {
        this.topics.get(topic)?.delete(handler as EventHandler<any>);
    }

    /**
     * Publish a payload on a topic.
     * @param topic - The topic (or subject) to publish to.
     * @param payload - The payload to send.
     */
    publish<T>(topic: string, payload: T): void {
        const handlers = this.topics.get(topic);
        if (handlers) {
            // Iterate over a copy in case a handler unsubscribes while iterating.
            for (const handler of Array.from(handlers)) {
                try {
                    handler(payload);
                } catch (err) {
                    console.error(`Error in handler for topic "${ topic }":`, err);
                }
            }
        }
    }
}

export default new EventBus();
