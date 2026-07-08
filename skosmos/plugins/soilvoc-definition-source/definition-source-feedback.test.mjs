import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

class FakeElement {
  constructor(tagName, id = "") {
    this.tagName = tagName;
    this.id = id;
    this.name = "";
    this.type = "";
    this.value = "";
    this.placeholder = "";
    this.rows = 0;
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
    if (name === "id") {
      this.id = value;
    }
    if (name === "name") {
      this.name = value;
    }
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

  closest(selector) {
    let element = this;
    const selectors = selector.split(",").map((part) => part.trim());
    while (element) {
      if (selectors.some((part) => element.matchesSelector(part))) {
        return element;
      }
      element = element.parentElement;
    }
    return null;
  }

  reportValidity() {
    return true;
  }

  matchesSelector(selector) {
    if (selector.startsWith("#")) {
      return this.id === selector.slice(1);
    }
    if (selector.startsWith(".")) {
      return this.className.split(/\s+/).includes(selector.slice(1));
    }

    const dataMatch = selector.match(/^\[data-soilvoc-feedback-template-field(?:=['"]([^'"]+)['"])?\]$/);
    if (dataMatch) {
      const expected = dataMatch[1];
      return this.dataset.soilvocFeedbackTemplateField !== undefined
        && (!expected || this.dataset.soilvocFeedbackTemplateField === expected);
    }

    const namedControlMatch = selector.match(/^(input|textarea|select)?(?:#([\w-]+)|\[name=['"]([^'"]+)['"]\])$/);
    if (namedControlMatch) {
      const [, tagName, id, name] = namedControlMatch;
      const tagMatches = !tagName || this.tagName.toLowerCase() === tagName;
      const idMatches = !id || this.id === id;
      const nameMatches = !name || this.name === name;
      return tagMatches && idMatches && nameMatches;
    }

    return this.tagName.toLowerCase() === selector.toLowerCase();
  }

  querySelector(selector) {
    for (const child of this.children) {
      if (child.matchesSelector(selector)) {
        return child;
      }
      const nested = child.querySelector(selector);
      if (nested) {
        return nested;
      }
    }
    return null;
  }

  querySelectorAll(selector) {
    const results = [];
    for (const child of this.children) {
      if (child.matchesSelector(selector)) {
        results.push(child);
      }
      results.push(...child.querySelectorAll(selector));
    }
    return results;
  }
}

const form = new FakeElement("form", "feedback-form");
const subjectField = new FakeElement("input");
subjectField.name = "msgsubject";
const messageField = new FakeElement("textarea");
messageField.name = "message";
const submitButton = new FakeElement("button", "submit-feedback");
form.appendChild(subjectField);
form.appendChild(messageField);
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
      pathname: "/en/feedback",
      href: "https://soilvoc.wangbeichen.com/en/feedback",
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
assert.ok(form.querySelector(".soilvoc-concept-suggestion"));
assert.equal(form.querySelectorAll("[data-soilvoc-feedback-template-field]").length, 8);

form.querySelector("[data-soilvoc-feedback-template-field='preferredTerm']").value = "soil enzyme activity";
form.querySelector("[data-soilvoc-feedback-template-field='broaderConcept']").value = "soil biological properties";
form.querySelector("[data-soilvoc-feedback-template-field='definition']").value = "Potential activity of soil enzymes.";
form.querySelector("[data-soilvoc-feedback-template-field='source']").value = "GLOSOLAN SOP";
form.querySelector("[data-soilvoc-feedback-template-field='externalMappings']").value = "AGROVOC / NALT candidates";
messageField.value = "Please consider adding this term.";
messageField.listeners.get("input")();

await form.listeners.get("submit")({
  preventDefault() {
    prevented = true;
  },
});

assert.equal(prevented, true);
assert.equal(subjectField.value, "Concept suggestion: soil enzyme activity");
assert.match(messageField.value, /Concept suggestion template/);
assert.match(messageField.value, /Proposed preferred term: soil enzyme activity/);
assert.match(messageField.value, /Suggested broader concept: soil biological properties/);
assert.match(messageField.value, /Additional notes:\nPlease consider adding this term/);
assert.equal(fetchCall.input, "https://soilvoc.wangbeichen.com/api/feedback");
assert.equal(fetchCall.options.method, "POST");
assert.equal(fetchCall.options.body.source, form);
assert.equal(submitButton.disabled, true);
assert.match(form.children[0].innerHTML, /Feedback has been sent/);
