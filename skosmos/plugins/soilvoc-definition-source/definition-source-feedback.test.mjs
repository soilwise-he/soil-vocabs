import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

class FakeElement {
  constructor(tagName, id = "") {
    this.tagName = tagName;
    this.id = id;
    this.children = [];
    this.dataset = {};
    this.className = "";
    this.attributes = new Map();
    this.listeners = new Map();
    this.parentElement = null;
    this.disabled = false;
    this.textContent = "";
    this.innerHTML = "";
  }

  setAttribute(name, value) {
    this.attributes.set(name, value);
  }

  appendChild(child) {
    child.parentElement = this;
    this.children.push(child);
    return child;
  }

  insertBefore(child, reference) {
    child.parentElement = this;
    const index = this.children.indexOf(reference);
    if (index === -1) {
      this.children.push(child);
    } else {
      this.children.splice(index, 0, child);
    }
    return child;
  }

  replaceChildren(...children) {
    this.children = [];
    for (const child of children) {
      this.appendChild(child);
    }
  }

  addEventListener(name, handler) {
    this.listeners.set(name, handler);
  }

  reportValidity() {
    return true;
  }

  querySelector(selector) {
    if (selector === "#submit-feedback") {
      return this.children.find((child) => child.id === "submit-feedback") || null;
    }
    if (selector === ".soilvoc-feedback-status") {
      return this.children.find((child) => child.className.includes("soilvoc-feedback-status")) || null;
    }
    if (selector === ".cf-turnstile") {
      return this.children.find((child) => child.className.includes("cf-turnstile")) || null;
    }
    return null;
  }
}

const form = new FakeElement("form", "feedback-form");
const submitButton = new FakeElement("button", "submit-feedback");
form.appendChild(submitButton);

let fetchCall = null;
let prevented = false;

const context = {
  console,
  document: {
    baseURI: "https://soilvoc.wangbeichen.com/soilvoc/en/feedback",
    head: new FakeElement("head"),
    createElement: (tagName) => new FakeElement(tagName),
    addEventListener() {},
    querySelector(selector) {
      if (selector === "#feedback-form") {
        return form;
      }
      return null;
    },
    querySelectorAll() {
      return [];
    },
  },
  fetch: async (input, options) => {
    fetchCall = { input, options };
    return new Response(JSON.stringify({ ok: true, messageId: "test-message-id" }), {
      status: 200,
      headers: { "content-type": "application/json" },
    });
  },
  FormData: class FakeFormData {
    constructor(source) {
      this.source = source;
    }
  },
  Response,
  URL,
  URLSearchParams,
  window: {
    fetch: async () => new Response("{}"),
    location: {
      pathname: "/soilvoc/en/feedback",
      href: "https://soilvoc.wangbeichen.com/soilvoc/en/feedback",
    },
  },
};
context.window.window = context.window;
context.window.document = context.document;

vm.runInNewContext(fs.readFileSync(new URL("./definition-source.js", import.meta.url), "utf8"), context);
context.window.soilvocDefinitionSource();

assert.equal(form.dataset.soilvocFeedbackWorker, "true");
assert.equal(form.action, "https://soilvoc.wangbeichen.com/api/feedback");
assert.equal(typeof form.listeners.get("submit"), "function");

await form.listeners.get("submit")({
  preventDefault() {
    prevented = true;
  },
});

assert.equal(prevented, true);
assert.equal(fetchCall.input, "https://soilvoc.wangbeichen.com/api/feedback");
assert.equal(fetchCall.options.method, "POST");
assert.equal(fetchCall.options.body.source, form);
assert.equal(submitButton.disabled, true);
assert.match(form.children[0].innerHTML, /Feedback has been sent/);
