import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { createFeedbackWorker } from "../src/worker.mjs";

function createRequest(body, headers = {}) {
  const form = new URLSearchParams(body);
  return new Request("https://soilvoc.wangbeichen.com/api/feedback", {
    method: "POST",
    headers: {
      "content-type": "application/x-www-form-urlencoded",
      origin: "https://soilvoc.wangbeichen.com",
      ...headers,
    },
    body: form,
  });
}

function createEnv(overrides = {}) {
  const sent = [];
  return {
    env: {
      FEEDBACK_TO: "owner@example.com",
      FEEDBACK_FROM: "feedback@wangbeichen.com",
      ALLOWED_ORIGIN: "https://soilvoc.wangbeichen.com",
      EMAIL: {
        send: async (message) => {
          sent.push(message);
          return { messageId: "test-message-id" };
        },
      },
      ...overrides,
    },
    sent,
  };
}

async function json(response) {
  return response.json();
}

describe("soilvoc feedback worker", () => {
  it("returns a health response for GET", async () => {
    const worker = createFeedbackWorker();
    const { env } = createEnv();

    const response = await worker.fetch(new Request("https://soilvoc.wangbeichen.com/api/feedback"), env);

    assert.equal(response.status, 200);
    assert.match(await response.text(), /SoilVoc feedback endpoint/);
  });

  it("rejects requests from unexpected origins", async () => {
    const worker = createFeedbackWorker();
    const { env, sent } = createEnv();

    const response = await worker.fetch(
      createRequest({ msgsubject: "Hello", message: "Body" }, { origin: "https://example.com" }),
      env,
    );

    assert.equal(response.status, 403);
    assert.equal(sent.length, 0);
  });

  it("rejects missing required fields", async () => {
    const worker = createFeedbackWorker();
    const { env, sent } = createEnv();

    const response = await worker.fetch(createRequest({ msgsubject: "", message: "" }), env);
    const data = await json(response);

    assert.equal(response.status, 400);
    assert.equal(data.ok, false);
    assert.match(data.error, /subject/i);
    assert.equal(sent.length, 0);
  });

  it("quietly accepts honeypot spam without sending email", async () => {
    const worker = createFeedbackWorker();
    const { env, sent } = createEnv();

    const response = await worker.fetch(
      createRequest({
        msgsubject: "Hello",
        message: "Body",
        "item-description": "filled by bot",
      }),
      env,
    );
    const data = await json(response);

    assert.equal(response.status, 200);
    assert.equal(data.ok, true);
    assert.equal(sent.length, 0);
  });

  it("requires Turnstile token when a secret is configured", async () => {
    const worker = createFeedbackWorker({
      verifyTurnstile: async () => ({ success: true }),
    });
    const { env, sent } = createEnv({ TURNSTILE_SECRET: "secret" });

    const response = await worker.fetch(createRequest({ msgsubject: "Hello", message: "Body" }), env);
    const data = await json(response);

    assert.equal(response.status, 400);
    assert.equal(data.ok, false);
    assert.match(data.error, /verification/i);
    assert.equal(sent.length, 0);
  });

  it("sends feedback email after validation", async () => {
    const worker = createFeedbackWorker({
      verifyTurnstile: async (_token, _secret, remoteIp) => ({ success: Boolean(remoteIp) }),
    });
    const { env, sent } = createEnv({ TURNSTILE_SECRET: "secret" });

    const response = await worker.fetch(
      createRequest(
        {
          vocab: "soilvoc",
          name: "Ada",
          email: "ada@example.com",
          msgsubject: "A concept note",
          message: "Please review this concept.",
          "cf-turnstile-response": "valid-token",
        },
        { "cf-connecting-ip": "203.0.113.10" },
      ),
      env,
    );
    const data = await json(response);

    assert.equal(response.status, 200);
    assert.equal(data.ok, true);
    assert.equal(sent.length, 1);
    assert.equal(sent[0].to, "owner@example.com");
    assert.deepEqual(sent[0].replyTo, { email: "ada@example.com", name: "Ada" });
    assert.match(sent[0].subject, /\[SoilVoc feedback\] A concept note/);
    assert.match(sent[0].text, /Please review this concept/);
    assert.match(sent[0].text, /203.0.113.10/);
  });

  it("can expose email error codes during deployment testing", async () => {
    const worker = createFeedbackWorker();
    const { env } = createEnv({
      DEBUG_ERRORS: "true",
      EMAIL: {
        send: async () => {
          const error = new Error("sender not verified");
          error.code = "E_SENDER_NOT_VERIFIED";
          throw error;
        },
      },
    });

    const response = await worker.fetch(createRequest({ msgsubject: "Hello", message: "Body" }), env);
    const data = await json(response);

    assert.equal(response.status, 502);
    assert.equal(data.ok, false);
    assert.equal(data.errorCode, "E_SENDER_NOT_VERIFIED");
  });
});
