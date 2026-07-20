import Link from "next/link";

export function Footer() {
  return (
    <footer className="bg-[#050505] text-zinc-400 py-20 border-t border-zinc-900">
      <div className="max-w-[1280px] mx-auto px-6">
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-12 mb-20">
          <div className="col-span-2 lg:col-span-2">
            <Link href="/" className="flex items-center gap-2 mb-6">
              <img 
                src="/logo-white.png" 
                alt="VeriField" 
                className="h-6 w-auto object-contain"
              />
            </Link>
            <p className="text-sm leading-relaxed max-w-xs">
              The Climate Infrastructure Operating System. Deploy, monitor, and verify climate projects globally.
            </p>
          </div>
          
          <div>
            <h4 className="text-white font-medium mb-6">Platform</h4>
            <ul className="flex flex-col gap-4 text-sm">
              <li><Link href="#platform" className="hover:text-white transition-colors">Methodology Engine</Link></li>
              <li><Link href="#platform" className="hover:text-white transition-colors">Digital MRV</Link></li>
              <li><Link href="#platform" className="hover:text-white transition-colors">Compliance</Link></li>
              <li><Link href="#platform" className="hover:text-white transition-colors">Registry Integrations</Link></li>
            </ul>
          </div>

          <div>
            <h4 className="text-white font-medium mb-6">Solutions</h4>
            <ul className="flex flex-col gap-4 text-sm">
              <li><Link href="#industries" className="hover:text-white transition-colors">Clean Cookstoves</Link></li>
              <li><Link href="#industries" className="hover:text-white transition-colors">Hybrid Solar</Link></li>
              <li><Link href="#industries" className="hover:text-white transition-colors">Biochar</Link></li>
              <li><Link href="#industries" className="hover:text-white transition-colors">EV Mobility</Link></li>
            </ul>
          </div>

          <div>
            <h4 className="text-white font-medium mb-6">Company</h4>
            <ul className="flex flex-col gap-4 text-sm">
              <li><Link href="#about" className="hover:text-white transition-colors">About Us</Link></li>
              <li><Link href="#contact" className="hover:text-white transition-colors">Contact</Link></li>
              <li><Link href="/login" className="hover:text-white transition-colors">Sign In</Link></li>
              <li><Link href="/signup" className="hover:text-white transition-colors">Request Access</Link></li>
              <li className="pt-4 mt-2 border-t border-zinc-900 text-zinc-500">Lagos, Nigeria</li>
            </ul>
          </div>
        </div>

        <div className="flex flex-col md:flex-row items-center justify-between pt-8 border-t border-zinc-900 text-xs">
          <p>&copy; {new Date().getFullYear()} VeriField Technologies. All rights reserved.</p>
          <div className="flex items-center gap-6 mt-4 md:mt-0">
            <Link href="/privacy" className="hover:text-white transition-colors">Privacy Policy</Link>
            <Link href="/terms" className="hover:text-white transition-colors">Terms of Service</Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
