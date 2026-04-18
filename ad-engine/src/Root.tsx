import React from "react";
import { Composition, Folder } from "remotion";
import { ProductShowcase, ProductShowcaseSchema } from "./compositions/ProductShowcase";
import { UGCTestimonial, UGCTestimonialSchema } from "./compositions/UGCTestimonial";
import { CountdownSale, CountdownSaleSchema } from "./compositions/CountdownSale";
import { ComparisonAd, ComparisonAdSchema } from "./compositions/ComparisonAd";
import { CinematicReveal, CinematicRevealSchema } from "./compositions/CinematicReveal";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Folder name="Product-Ads">
        {/* Product Showcase — Hero product with animated features + pricing + CTA */}
        <Composition
          id="ProductShowcase"
          component={ProductShowcase}
          schema={ProductShowcaseSchema}
          durationInFrames={450}
          fps={30}
          width={1080}
          height={1920}
          defaultProps={{
            productName: "Premium Wireless Earbuds",
            productImage: "products/earbuds.png",
            price: "$79.99",
            originalPrice: "$129.99",
            discount: "38% OFF",
            features: [
              "Active Noise Cancellation",
              "40hr Battery Life",
              "IPX7 Waterproof",
            ],
            ctaText: "Shop Now",
            brandColor: "#FF6B35",
            accentColor: "#004E89",
          }}
        />

        {/* Square variant for Meta Feed */}
        <Composition
          id="ProductShowcase-Square"
          component={ProductShowcase}
          schema={ProductShowcaseSchema}
          durationInFrames={450}
          fps={30}
          width={1080}
          height={1080}
          defaultProps={{
            productName: "Premium Wireless Earbuds",
            productImage: "products/earbuds.png",
            price: "$79.99",
            originalPrice: "$129.99",
            discount: "38% OFF",
            features: [
              "Active Noise Cancellation",
              "40hr Battery Life",
              "IPX7 Waterproof",
            ],
            ctaText: "Shop Now",
            brandColor: "#FF6B35",
            accentColor: "#004E89",
          }}
        />
      </Folder>

      <Folder name="UGC-Ads">
        {/* UGC Testimonial — AI avatar delivering script with captions */}
        <Composition
          id="UGCTestimonial"
          component={UGCTestimonial}
          schema={UGCTestimonialSchema}
          durationInFrames={450}
          fps={30}
          width={1080}
          height={1920}
          defaultProps={{
            hookText: "I was skeptical at first...",
            testimonialLines: [
              "I've tried so many products like this",
              "But this one actually changed everything",
              "The quality is insane for the price",
              "I've already bought 3 more for gifts",
            ],
            productName: "Premium Wireless Earbuds",
            productImage: "products/earbuds.png",
            rating: 5,
            reviewerName: "Sarah M.",
            ctaText: "Get Yours Today",
            brandColor: "#FF6B35",
          }}
        />
      </Folder>

      <Folder name="Sale-Ads">
        {/* Countdown Sale — Urgency timer + flashing discount */}
        <Composition
          id="CountdownSale"
          component={CountdownSale}
          schema={CountdownSaleSchema}
          durationInFrames={450}
          fps={30}
          width={1080}
          height={1920}
          defaultProps={{
            productName: "Premium Wireless Earbuds",
            productImage: "products/earbuds.png",
            originalPrice: "$129.99",
            salePrice: "$79.99",
            discount: "38% OFF",
            urgencyText: "FLASH SALE ENDS IN",
            hoursLeft: 4,
            minutesLeft: 32,
            ctaText: "Claim Deal",
            brandColor: "#E63946",
            accentColor: "#FFD166",
          }}
        />
      </Folder>

      <Folder name="Comparison-Ads">
        {/* Comparison Ad — Side-by-side feature comparison */}
        <Composition
          id="ComparisonAd"
          component={ComparisonAd}
          schema={ComparisonAdSchema}
          durationInFrames={450}
          fps={30}
          width={1080}
          height={1920}
          defaultProps={{
            headline: "Why Customers Switch",
            ourProduct: "Premium Earbuds",
            competitor: "Brand X",
            ourPrice: "$79.99",
            competitorPrice: "$149.99",
            comparisons: [
              { feature: "Battery Life", ours: "40 hours", theirs: "20 hours" },
              { feature: "Noise Cancel", ours: "ANC Pro", theirs: "Basic" },
              { feature: "Waterproof", ours: "IPX7", theirs: "IPX4" },
              { feature: "Warranty", ours: "2 Years", theirs: "90 Days" },
            ],
            ctaText: "See The Difference",
            brandColor: "#2ECC71",
          }}
        />
      </Folder>

      <Folder name="Cinematic">
        {/* Cinematic Reveal — Premium product entrance */}
        <Composition
          id="CinematicReveal"
          component={CinematicReveal}
          schema={CinematicRevealSchema}
          durationInFrames={300}
          fps={30}
          width={1080}
          height={1920}
          defaultProps={{
            productName: "Premium Wireless Earbuds",
            productImage: "products/earbuds.png",
            tagline: "Sound Without Limits",
            price: "$79.99",
            brandColor: "#1a1a2e",
            accentColor: "#e94560",
          }}
        />
      </Folder>
    </>
  );
};
