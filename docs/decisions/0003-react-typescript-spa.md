# 0003. React and TypeScript form a single-page client

- Status: accepted
- Date: 2026-11-22

## Context

Investigators need a case workspace: tables, a graph, an upload, and a copilot
panel, all behind a login. The application is not a public content site.
Server-rendering case data would create a second place where financial records
can leak into HTML caches and logs.

The graph drawing library has to be mature enough for directed, labelled edges.
Cytoscape.js meets that need in the browser. The server still computes the
subgraph.

## Decision

The client is a Vite-built React and TypeScript single-page application. React
Router handles screens. TanStack Query holds server state. Cytoscape.js draws
the graph the API returns. No component framework is required in Phase 1.

The browser calls only the VAGEXA API. It does not call a model provider or a
database.

## Consequences

- TypeScript types track the API. They do not become a second implementation of FIFO.
- Search engines and anonymous sharing are irrelevant and are not features.
- A future server-rendered page would need a specific reason, such as a
  locked-down export view, and a new ADR.

## Alternatives

- Next.js. Capable, and unnecessary for an authenticated tool. Rejected so
  case data is not rendered on a server by default.
- Vue or Angular. Viable. Rejected only because the client team of libraries
  around React and Cytoscape is the one this design will actually use. There is
  no product requirement that forces React beyond that fit.
- Server-generated HTML without a client graph library. Rejected because the
  investigator has to pan and inspect a graph locally.
