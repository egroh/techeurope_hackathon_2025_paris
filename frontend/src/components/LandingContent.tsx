"use client";

import React from "react";

// You can pass props to this component if needed, e.g., for text content
interface LandingContentProps {
  title: string;
  description: string;
  buttonText: string;
}

export default function LandingContent({ title, description, buttonText }: LandingContentProps) {
  const handleButtonClick = () => {
    // Replace with your actual navigation or action
    // For example, using Next.js router:
    // import { useRouter } from 'next/navigation';
    // const router = useRouter();
    // router.push('/some-other-page');
    alert("Let's get started!");
  };

  return (
    <div className="relative z-10 flex flex-col items-center justify-center w-full h-full p-4 text-center">
      {/* Logo - Assuming it's an SVG or image that might not need a text shadow */}
      <div className="mb-8">
        {/* Replace with your actual logo. This is a placeholder SVG. */}
        <svg
          className="w-24 h-24 text-cyan-400 md:w-32 md:h-32 animate-pulse"
          fill="currentColor"
          viewBox="0 0 200 200"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            d="M100 20C55.817 20 20 55.817 20 100s35.817 80 80 80 80-35.817 80-80S144.183 20 100 20zm0 140c-33.086 0-60-26.914-60-60s26.914-60 60-60 60 26.914 60 60-26.914 60-60 60z"
            fillOpacity="0.3"
          ></path>
          <path d="M100 50c-27.614 0-50 22.386-50 50s22.386 50 50 50 50-22.386 50-50-22.386-50-50-50zm0 80c-16.568 0-30-13.432-30-30s13.432-30 30-30 30 13.432 30 30-13.432 30-30 30z"></path>
          <circle cx="100" cy="100" r="10"></circle>
        </svg>
        {/* Example using an image:
        <img
          src="/your-logo.svg" // Place your logo in the `public` folder
          alt="Our Awesome Logo"
          className="w-40 h-auto md:w-56"
        />
        */}
      </div>

      {/* Title / Welcome Message */}
      <h1 className="mb-4 text-4xl font-extrabold leading-tight tracking-tight text-transparent md:text-6xl lg:text-7xl bg-clip-text bg-gradient-to-r from-cyan-400 via-pink-500 to-yellow-400 drop-shadow-md md:drop-shadow-lg [text-shadow:0_0_8px_rgba(0,0,0,0.7)]">
        {title}
      </h1>
      <p className="max-w-xl mx-auto mb-8 text-lg text-gray-300 md:text-xl lg:max-w-2xl drop-shadow-sm md:drop-shadow-md [text-shadow:0_0_5px_rgba(0,0,0,0.7)]">
        {description}
      </p>

      {/* Call to Action Button */}
      <button
        className="px-10 py-3 text-lg font-semibold text-black transition duration-300 ease-in-out transform border-2 border-transparent rounded-lg shadow-xl bg-gradient-to-r from-cyan-400 to-fuchsia-500 hover:from-cyan-500 hover:to-fuchsia-600 hover:scale-105 focus:outline-none focus:ring-4 focus:ring-pink-500 focus:ring-opacity-50"
        onClick={handleButtonClick}
      >
        {buttonText}
      </button>
    </div>
  );
}
