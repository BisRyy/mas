declare module "plotly.js-dist-min" {
  // Re-export plotly's types under the dist-min module name.
  // Plotly ships its TypeScript types in plotly.js; the dist-min build
  // is just a smaller bundle of the same library.
  export * from "plotly.js";
}
