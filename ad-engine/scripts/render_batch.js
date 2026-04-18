/**
 * render_batch.js — Read products.json → render Remotion ads for each product
 *
 * Usage:
 *   node scripts/render_batch.js
 *   node scripts/render_batch.js --template ProductShowcase
 *   node scripts/render_batch.js --format square
 *   node scripts/render_batch.js --limit 5 --parallel 2
 *
 * Templates:    ProductShowcase | UGCTestimonial | CountdownSale | ComparisonAd | CinematicReveal
 * Formats:      vertical (1080x1920) | square (1080x1080) | landscape (1920x1080)
 * Default:      all templates, vertical format
 */

"use strict";

const fs = require("fs");
const path = require("path");
const { execSync, spawn } = require("child_process");

// Load .env from project root if present
try {
  require("dotenv").config({ path: path.join(__dirname, "..", ".env") });
} catch {
  // dotenv optional
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const PROJECT_ROOT = path.join(__dirname, "..");
const PRODUCTS_JSON = path.join(PROJECT_ROOT, "products.json");
const EXPORTS_DIR = path.join(PROJECT_ROOT, "exports");

const ALL_TEMPLATES = [
  "ProductShowcase",
  "UGCTestimonial",
  "CountdownSale",
  "ComparisonAd",
  "CinematicReveal",
];

const FORMAT_DIMENSIONS = {
  vertical: { width: 1080, height: 1920 },
  square: { width: 1080, height: 1080 },
  landscape: { width: 1920, height: 1080 },
};

// Default brand colors used when a product has no tags to derive them from
const DEFAULT_BRAND_COLOR = "#FF6B35";
const DEFAULT_ACCENT_COLOR = "#004E89";

// How many hours the CountdownSale timer starts at by default
const DEFAULT_HOURS_LEFT = 4;
const DEFAULT_MINUTES_LEFT = 0;

// ---------------------------------------------------------------------------
// CLI arg parsing
// ---------------------------------------------------------------------------

function parseArgs() {
  const args = process.argv.slice(2);
  const get = (flag) => {
    const idx = args.indexOf(flag);
    return idx !== -1 ? args[idx + 1] : null;
  };
  const has = (flag) => args.includes(flag);

  const rawTemplate = get("--template");
  const rawFormat = get("--format");
  const rawLimit = get("--limit");
  const rawParallel = get("--parallel");

  // Validate template
  let templates = ALL_TEMPLATES;
  if (rawTemplate) {
    if (!ALL_TEMPLATES.includes(rawTemplate)) {
      console.error(
        `Error: Unknown template "${rawTemplate}".\n` +
          `Valid options: ${ALL_TEMPLATES.join(", ")}`
      );
      process.exit(1);
    }
    templates = [rawTemplate];
  }

  // Validate format
  let format = "vertical";
  if (rawFormat) {
    if (!FORMAT_DIMENSIONS[rawFormat]) {
      console.error(
        `Error: Unknown format "${rawFormat}".\n` +
          `Valid options: ${Object.keys(FORMAT_DIMENSIONS).join(", ")}`
      );
      process.exit(1);
    }
    format = rawFormat;
  }

  // Validate limit
  let limit = Infinity;
  if (rawLimit !== null) {
    limit = parseInt(rawLimit, 10);
    if (isNaN(limit) || limit < 1) {
      console.error("Error: --limit must be a positive integer.");
      process.exit(1);
    }
  }

  // Validate parallel
  let parallel = 1;
  if (rawParallel !== null) {
    parallel = parseInt(rawParallel, 10);
    if (isNaN(parallel) || parallel < 1) {
      console.error("Error: --parallel must be a positive integer.");
      process.exit(1);
    }
  }

  return { templates, format, limit, parallel };
}

// ---------------------------------------------------------------------------
// Product → Remotion props mapping
// ---------------------------------------------------------------------------

/**
 * Derive a brand color from product tags if present.
 * Supports tags like "brand-color:#FF6B35" or simply falls back to default.
 */
function deriveBrandColor(tags) {
  if (!tags || !Array.isArray(tags)) return DEFAULT_BRAND_COLOR;
  const colorTag = tags.find((t) => t.toLowerCase().startsWith("brand-color:"));
  return colorTag ? colorTag.split(":")[1].trim() : DEFAULT_BRAND_COLOR;
}

function deriveAccentColor(tags) {
  if (!tags || !Array.isArray(tags)) return DEFAULT_ACCENT_COLOR;
  const colorTag = tags.find((t) => t.toLowerCase().startsWith("accent-color:"));
  return colorTag ? colorTag.split(":")[1].trim() : DEFAULT_ACCENT_COLOR;
}

/**
 * Extract up to 3 features from product tags (tags prefixed with "feature:").
 * Falls back to productType + generic ad copy if no feature tags found.
 */
function deriveFeatures(product) {
  const featureTags = (product.tags || [])
    .filter((t) => t.toLowerCase().startsWith("feature:"))
    .map((t) => t.replace(/^feature:/i, "").trim())
    .slice(0, 3);

  if (featureTags.length >= 2) return featureTags;

  // Generate sensible fallbacks from productType and discount
  const fallbacks = [];
  if (product.productType) fallbacks.push(product.productType);
  if (product.discount) fallbacks.push(`Save ${product.discount}`);
  if (product.tags?.includes("bestseller")) fallbacks.push("Bestseller");
  if (product.tags?.includes("new")) fallbacks.push("New Arrival");
  fallbacks.push("Free Shipping");
  fallbacks.push("30-Day Returns");

  return [...featureTags, ...fallbacks].slice(0, 3);
}

/**
 * Build a product-specific tagline for CinematicReveal from tags or title.
 */
function deriveTagline(product) {
  const taglineTags = (product.tags || []).filter((t) =>
    t.toLowerCase().startsWith("tagline:")
  );
  if (taglineTags.length > 0) {
    return taglineTags[0].replace(/^tagline:/i, "").trim();
  }
  // Fall back to a short excerpt of the description, or generic copy
  if (product.description && product.description.length > 0) {
    const words = product.description.split(/\s+/).slice(0, 6).join(" ");
    return words.length > 0 ? words : "Experience the Difference";
  }
  return "Experience the Difference";
}

/**
 * Build the productImage path for Remotion props.
 * Prefers the local cached image (staticFile-compatible), falls back to first remote URL.
 */
function resolveProductImage(product) {
  if (product.localImage) return product.localImage;
  // If no local image, Remotion can still render with a remote URL via <Img>
  // but for best results the sync script should have downloaded it
  return product.images?.[0] ?? "";
}

/**
 * Build testimonial lines from product description.
 * Splits on sentences or uses placeholder lines that reference the product.
 */
function deriveTestimonialLines(product) {
  const lines = [];

  if (product.description) {
    // Split into sentences and take first 4, capped at ~60 chars each for readability
    const sentences = product.description
      .replace(/\n+/g, " ")
      .split(/(?<=[.!?])\s+/)
      .map((s) => s.trim())
      .filter((s) => s.length > 10 && s.length < 120)
      .slice(0, 4);

    if (sentences.length >= 2) return sentences;
  }

  // Generic fallback lines
  lines.push(`I was skeptical about ${product.title}`);
  lines.push("But the quality completely blew me away");
  if (product.discount) lines.push(`And getting it at ${product.discount} was a bonus`);
  else lines.push("Absolutely worth every penny");
  lines.push("Already ordered two more for gifts");

  return lines;
}

/**
 * Map a product to props for a specific Remotion composition.
 * Returns null if a required prop cannot be derived (e.g. no price for PriceScene).
 */
function buildProps(product, template) {
  const brandColor = deriveBrandColor(product.tags);
  const accentColor = deriveAccentColor(product.tags);
  const productImage = resolveProductImage(product);
  const price = product.price ?? "$0.00";
  const compareAtPrice = product.compareAtPrice ?? price;
  const discount = product.discount ?? "SALE";

  switch (template) {
    case "ProductShowcase":
      return {
        productName: product.title,
        productImage,
        price,
        originalPrice: compareAtPrice,
        discount,
        features: deriveFeatures(product),
        ctaText: "Shop Now",
        brandColor,
        accentColor,
      };

    case "UGCTestimonial":
      return {
        hookText: `I was skeptical at first...`,
        testimonialLines: deriveTestimonialLines(product),
        productName: product.title,
        productImage,
        rating: 5,
        reviewerName: "Verified Buyer",
        ctaText: "Get Yours Today",
        brandColor,
      };

    case "CountdownSale":
      return {
        productName: product.title,
        productImage,
        originalPrice: compareAtPrice,
        salePrice: price,
        discount,
        urgencyText: "FLASH SALE ENDS IN",
        hoursLeft: DEFAULT_HOURS_LEFT,
        minutesLeft: DEFAULT_MINUTES_LEFT,
        ctaText: "Claim Deal",
        brandColor,
        accentColor,
      };

    case "ComparisonAd": {
      const features = deriveFeatures(product);
      // Build a generic comparison table from features and price
      const comparisons = features.map((feat) => ({
        feature: feat,
        ours: "✓ Included",
        theirs: "✗ Missing",
      }));
      // Ensure there's at least one comparison row
      if (comparisons.length === 0) {
        comparisons.push({ feature: "Quality", ours: "Premium", theirs: "Basic" });
      }
      comparisons.push({ feature: "Price", ours: price, theirs: "More expensive" });

      return {
        headline: "Why Customers Switch",
        ourProduct: product.title,
        competitor: "Leading Brand",
        ourPrice: price,
        competitorPrice: compareAtPrice,
        comparisons: comparisons.slice(0, 5),
        ctaText: "See The Difference",
        brandColor,
      };
    }

    case "CinematicReveal":
      return {
        productName: product.title,
        productImage,
        tagline: deriveTagline(product),
        price,
        brandColor,
        accentColor,
      };

    default:
      return null;
  }
}

// ---------------------------------------------------------------------------
// Remotion composition ID resolution
// Note: Root.tsx registers square variants as "ProductShowcase-Square".
// For non-standard formats, the composition ID maps to the same component.
// We use the base composition ID for vertical, and append the format suffix
// for square/landscape to match what's registered in Root.tsx.
// Since only ProductShowcase has an explicit square registration we use the
// base ID for all formats — Remotion accepts the same component at any size
// via --width/--height overrides on the CLI.
// ---------------------------------------------------------------------------

/**
 * Resolve the Remotion composition ID for a template + format combination.
 * ProductShowcase has a registered Square variant; all others use the base ID.
 */
function resolveCompositionId(template, format) {
  if (template === "ProductShowcase" && format === "square") {
    return "ProductShowcase-Square";
  }
  return template;
}

// ---------------------------------------------------------------------------
// Single render job
// ---------------------------------------------------------------------------

/**
 * Render one product × one template × one format.
 * Returns { success, outputPath, error }.
 */
function renderOne(product, template, format) {
  return new Promise((resolve) => {
    const { width, height } = FORMAT_DIMENSIONS[format];
    const compositionId = resolveCompositionId(template, format);

    // Sanitize handle for filesystem use
    const safeHandle = (product.handle || product.title)
      .toLowerCase()
      .replace(/[^a-z0-9-]/g, "-")
      .replace(/-+/g, "-")
      .replace(/^-|-$/g, "");

    const outputDir = path.join(EXPORTS_DIR, safeHandle);
    const outputFile = path.join(outputDir, `${template}-${format}.mp4`);

    fs.mkdirSync(outputDir, { recursive: true });

    const props = buildProps(product, template);
    if (!props) {
      resolve({
        success: false,
        outputPath: outputFile,
        error: `No props mapping for template "${template}"`,
      });
      return;
    }

    // Serialize props as a temp JSON file so the Remotion CLI can consume it.
    // Passing large JSON inline via --props can hit shell arg length limits on Windows.
    const propsFile = path.join(
      PROJECT_ROOT,
      `tmp-props-${safeHandle}-${template}.json`
    );
    fs.writeFileSync(propsFile, JSON.stringify(props), "utf8");

    const args = [
      "remotion",
      "render",
      compositionId,
      outputFile,
      "--props",
      propsFile,
      "--width",
      String(width),
      "--height",
      String(height),
      "--log",
      "error", // suppress Remotion's verbose frame output
    ];

    const proc = spawn("npx", args, {
      cwd: PROJECT_ROOT,
      stdio: ["ignore", "ignore", "pipe"], // capture stderr only for error messages
    });

    let stderrOutput = "";
    proc.stderr.on("data", (chunk) => {
      stderrOutput += chunk.toString();
    });

    proc.on("close", (code) => {
      // Clean up temp props file
      try {
        fs.unlinkSync(propsFile);
      } catch {
        // Non-fatal
      }

      if (code === 0) {
        resolve({ success: true, outputPath: outputFile, error: null });
      } else {
        // Trim stderr to first meaningful line for readability
        const errorMsg = stderrOutput
          .split("\n")
          .map((l) => l.trim())
          .filter(Boolean)
          .slice(0, 3)
          .join(" | ");
        resolve({
          success: false,
          outputPath: outputFile,
          error: errorMsg || `Process exited with code ${code}`,
        });
      }
    });

    proc.on("error", (err) => {
      try {
        fs.unlinkSync(propsFile);
      } catch {
        // Non-fatal
      }
      resolve({ success: false, outputPath: outputFile, error: err.message });
    });
  });
}

// ---------------------------------------------------------------------------
// Batch execution with concurrency control
// ---------------------------------------------------------------------------

/**
 * Run an array of async task functions with a concurrency cap.
 */
async function runWithConcurrency(tasks, maxConcurrent) {
  const results = [];
  const queue = [...tasks];
  const active = new Set();

  return new Promise((resolve) => {
    function tryStart() {
      while (active.size < maxConcurrent && queue.length > 0) {
        const task = queue.shift();
        const promise = task().then((result) => {
          active.delete(promise);
          results.push(result);
          tryStart();
          if (active.size === 0 && queue.length === 0) {
            resolve(results);
          }
        });
        active.add(promise);
      }
    }

    if (queue.length === 0) {
      resolve(results);
    } else {
      tryStart();
    }
  });
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main() {
  const { templates, format, limit, parallel } = parseArgs();

  // Read products.json
  if (!fs.existsSync(PRODUCTS_JSON)) {
    console.error(
      `Error: products.json not found at ${PRODUCTS_JSON}\n` +
        "Run 'npm run shopify:sync' first to fetch products from Shopify."
    );
    process.exit(1);
  }

  let products;
  try {
    products = JSON.parse(fs.readFileSync(PRODUCTS_JSON, "utf8"));
  } catch (err) {
    console.error(`Error: Failed to parse products.json: ${err.message}`);
    process.exit(1);
  }

  if (!Array.isArray(products) || products.length === 0) {
    console.error("Error: products.json is empty or malformed.");
    process.exit(1);
  }

  // Apply limit
  const targetProducts = products.slice(0, isFinite(limit) ? limit : undefined);

  const totalJobs = targetProducts.length * templates.length;

  console.log("\nShopify Ad Engine — Batch Renderer");
  console.log("─".repeat(50));
  console.log(`Products:  ${targetProducts.length} of ${products.length}`);
  console.log(`Templates: ${templates.join(", ")}`);
  console.log(`Format:    ${format} (${FORMAT_DIMENSIONS[format].width}x${FORMAT_DIMENSIONS[format].height})`);
  console.log(`Jobs:      ${totalJobs}`);
  console.log(`Parallel:  ${parallel}`);
  console.log(`Output:    ${EXPORTS_DIR}`);
  console.log("─".repeat(50) + "\n");

  // Ensure exports dir exists
  fs.mkdirSync(EXPORTS_DIR, { recursive: true });

  // Ensure tmp dir exists for props files
  fs.mkdirSync(path.join(PROJECT_ROOT, "tmp-props"), { recursive: true });

  let completed = 0;
  let succeeded = 0;
  let failed = 0;
  const failures = [];

  // Build all tasks
  const tasks = [];
  for (const product of targetProducts) {
    for (const template of templates) {
      tasks.push(() => {
        const jobNum = ++completed;
        const label = `[${jobNum}/${totalJobs}] ${product.title.slice(0, 30)} — ${template} (${format})`;
        process.stdout.write(`Rendering ${label}...`);

        return renderOne(product, template, format).then((result) => {
          if (result.success) {
            succeeded++;
            process.stdout.write(" done\n");
          } else {
            failed++;
            process.stdout.write(` FAILED\n`);
            process.stderr.write(`  Error: ${result.error}\n`);
            failures.push({
              product: product.title,
              template,
              format,
              error: result.error,
            });
          }
          return result;
        });
      });
    }
  }

  // Execute with concurrency control
  await runWithConcurrency(tasks, parallel);

  // Summary
  console.log("\n" + "─".repeat(50));
  console.log(
    `Rendered ${succeeded} ads for ${targetProducts.length} product${targetProducts.length === 1 ? "" : "s"}. Saved to exports/`
  );

  if (failed > 0) {
    console.log(`\nFailed renders (${failed}):`);
    for (const f of failures) {
      console.log(`  ${f.product} — ${f.template} (${f.format}): ${f.error}`);
    }
  }

  console.log();
}

main().catch((err) => {
  console.error(`Unexpected error: ${err.message}`);
  process.exit(1);
});
