import NeonIsometricMaze from "@/components/neon-isometric-maze";
import LandingContent from "@/components/LandingContent";

export default function LandingPage() {
  const pageContent = {
    title: "Your Awesome Project",
    description: "Discover the amazing features we offer, all wrapped in a stunning visual experience.",
    buttonText: "Explore Now",
  };

  return (
    <div className="relative w-screen h-screen overflow-hidden bg-black">
      {/* Background Maze: Positioned to fill, behind other content */}
      <div className="absolute inset-0 z-0">
        <NeonIsometricMaze />
      </div>

      {/* Foreground Content Overlay: Now using the Client Component */}
      <LandingContent
        title={pageContent.title}
        description={pageContent.description}
        buttonText={pageContent.buttonText}
      />
    </div>
  );
}
