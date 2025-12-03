import ShaderViewer from "@/components/ShaderViewer";
import Verify from "@/components/Verify";

export default function Home() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-zinc-50 font-sans dark:bg-black">
      <section className="h-screen w-3/5 ">
        <ShaderViewer />
      </section>

      <section className="h-screen w-2/5 ">
        <Verify />
      </section>
    </div>
  );
}
