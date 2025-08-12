import { ArrowRight, Shield, Users, Lock, Brain, CheckCircle, XCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import Link from 'next/link'
import DocumentIntelligenceDashboard from '@/components/document-intelligence-dashboard'

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-white">
      {/* Navigation */}
      <nav className="border-b border-gray-100 bg-white/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-2">
              <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
                <Brain className="w-5 h-5 text-white" />
              </div>
              <span className="text-xl font-semibold text-gray-900">Orris</span>
            </div>
            <div className="hidden md:flex items-center space-x-8">
              <Link href="/login">
                <Button variant="ghost" className="text-gray-600">Sign In</Button>
              </Link>
              <Link href="/signup">
                <Button className="bg-blue-600 hover:bg-blue-700">Get Started</Button>
              </Link>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="pt-20 pb-16 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto text-center">
          <div className="mb-8">
            <div className="inline-flex items-center px-4 py-2 bg-blue-50 rounded-full text-sm text-blue-700 mb-6">
              <Shield className="w-4 h-4 mr-2" />
              Enterprise-grade security & privacy
            </div>
          </div>
          
          <h1 className="text-5xl md:text-6xl font-bold mb-8 leading-tight">
  <span className="bg-gradient-to-r from-gray-900 via-blue-900 to-gray-900 bg-clip-text text-transparent">
    Your secure knowledge partner –
  </span>
  <br />
  <span className="text-blue-600">Knows it all</span>,{' '}
  <span className="text-green-600">Spills just enough.</span>
</h1>
          
          <p className="text-xl text-gray-600 mb-10 max-w-3xl mx-auto leading-relaxed">
            AI-powered RAG system that syncs with Google Drive, intelligently classifies PI/Non-PI data, 
            and ensures users only access information they're authorized to see.
          </p>
          
          <div className="flex flex-col sm:flex-row gap-4 justify-center mb-16">
            <Link href="/signup">
              <Button size="lg" className="bg-blue-600 hover:bg-blue-700 text-lg px-8 py-4">
                Get Started <ArrowRight className="ml-2 w-5 h-5" />
              </Button>
            </Link>
            <Button size="lg" variant="outline" className="text-lg px-8 py-4">
              Request Demo
            </Button>
          </div>

          {/* Use Case Examples */}
          <div className="max-w-4xl mx-auto grid md:grid-cols-2 gap-6 mb-20">
            <Card className="border-green-200 bg-green-50">
              <CardContent className="p-6">
                <div className="flex items-start space-x-3">
                  <CheckCircle className="w-6 h-6 text-green-600 mt-1 flex-shrink-0" />
                  <div className="text-left">
                    <p className="font-medium text-gray-900 mb-2">
                      "What's our remote work policy?"
                    </p>
                    <p className="text-gray-600 text-sm">
                      "Based on accessible documents: Employees can work remotely up to 3 days per week with manager approval..."
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
            
            <Card className="border-red-200 bg-red-50">
              <CardContent className="p-6">
                <div className="flex items-start space-x-3">
                  <XCircle className="w-6 h-6 text-red-600 mt-1 flex-shrink-0" />
                  <div className="text-left">
                    <p className="font-medium text-gray-900 mb-2">
                      "Show me salary information"
                    </p>
                    <p className="text-gray-600 text-sm">
                      "Access denied. This query involves PI data that you don't have permission to access."
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      {/* Document Intelligence Dashboard */}
      <DocumentIntelligenceDashboard />

      {/* Features Section */}
      <section id="features" className="py-20 bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-gray-900 mb-4">
              Intelligent RAG with bulletproof access control
            </h2>
            <p className="text-xl text-gray-600 max-w-2xl mx-auto">
              Seamlessly sync Google Drive, classify sensitive data, and deliver precise answers while maintaining strict security
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
  <Card className="border-0 shadow-lg hover:shadow-xl transition-all duration-300 bg-gradient-to-br from-white to-blue-50 group">
    <CardContent className="p-8 text-center">
      <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-blue-600 rounded-2xl flex items-center justify-center mx-auto mb-6 group-hover:scale-110 transition-transform duration-300 shadow-lg">
        <Brain className="w-8 h-8 text-white" />
      </div>
      <h3 className="text-xl font-bold text-gray-900 mb-4">RAG-Powered Answers</h3>
      <p className="text-gray-600 leading-relaxed">
        Advanced retrieval system that finds relevant information across your Google Drive documents instantly
      </p>
    </CardContent>
  </Card>

  <Card className="border-0 shadow-lg hover:shadow-xl transition-all duration-300 bg-gradient-to-br from-white to-green-50 group">
    <CardContent className="p-8 text-center">
      <div className="w-16 h-16 bg-gradient-to-br from-green-500 to-green-600 rounded-2xl flex items-center justify-center mx-auto mb-6 group-hover:scale-110 transition-transform duration-300 shadow-lg">
        <Shield className="w-8 h-8 text-white" />
      </div>
      <h3 className="text-xl font-bold text-gray-900 mb-4">PI/Non-PI Classification</h3>
      <p className="text-gray-600 leading-relaxed">
        Automatically identifies and protects personal information while keeping non-sensitive data accessible
      </p>
    </CardContent>
  </Card>

  <Card className="border-0 shadow-lg hover:shadow-xl transition-all duration-300 bg-gradient-to-br from-white to-purple-50 group">
    <CardContent className="p-8 text-center">
      <div className="w-16 h-16 bg-gradient-to-br from-purple-500 to-purple-600 rounded-2xl flex items-center justify-center mx-auto mb-6 group-hover:scale-110 transition-transform duration-300 shadow-lg">
        <Users className="w-8 h-8 text-white" />
      </div>
      <h3 className="text-xl font-bold text-gray-900 mb-4">Access Control</h3>
      <p className="text-gray-600 leading-relaxed">
        Respects Google Drive permissions - users only see answers from documents they have access to
      </p>
    </CardContent>
  </Card>

  <Card className="border-0 shadow-lg hover:shadow-xl transition-all duration-300 bg-gradient-to-br from-white to-orange-50 group">
    <CardContent className="p-8 text-center">
      <div className="w-16 h-16 bg-gradient-to-br from-orange-500 to-orange-600 rounded-2xl flex items-center justify-center mx-auto mb-6 group-hover:scale-110 transition-transform duration-300 shadow-lg">
        <Lock className="w-8 h-8 text-white" />
      </div>
      <h3 className="text-xl font-bold text-gray-900 mb-4">Google Drive Sync</h3>
      <p className="text-gray-600 leading-relaxed">
        Real-time synchronization with your Google Drive, automatically indexing new documents as they're added
      </p>
    </CardContent>
  </Card>
</div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-24 bg-gradient-to-br from-blue-50 via-white to-indigo-50 relative overflow-hidden">
  {/* Background Pattern */}
  <div className="absolute inset-0 bg-grid-slate-100 [mask-image:linear-gradient(0deg,white,rgba(255,255,255,0.6))] -z-10"></div>
  
  <div className="max-w-6xl mx-auto text-center px-4 sm:px-6 lg:px-8 relative">
    <div className="max-w-3xl mx-auto">
      <h2 className="text-5xl font-bold text-gray-900 mb-6 leading-tight">
        Experience the Future of 
        <span className="bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent"> Enterprise AI</span>
      </h2>
      <p className="text-xl text-gray-600 mb-12 leading-relaxed">
        Join forward-thinking companies who've already transformed their knowledge management. 
        See measurable improvements in team productivity and information security from day one.
      </p>
      
      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-12">
        <div className="text-center">
          <div className="text-3xl font-bold text-blue-600 mb-2">98%</div>
          <div className="text-sm text-gray-600">Query Accuracy</div>
        </div>
        <div className="text-center">
          <div className="text-3xl font-bold text-green-600 mb-2">60%</div>
          <div className="text-sm text-gray-600">Time Saved</div>
        </div>
        <div className="text-center">
          <div className="text-3xl font-bold text-purple-600 mb-2">100%</div>
          <div className="text-sm text-gray-600">Access Control</div>
        </div>
      </div>
      
      <div className="flex flex-col sm:flex-row gap-4 justify-center">
        <Link href="/signup">
          <Button size="lg" className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white shadow-lg hover:shadow-xl transition-all duration-300 text-lg px-10 py-6">
            Start Free Trial
            <ArrowRight className="ml-2 w-5 h-5" />
          </Button>
        </Link>
        <Button size="lg" variant="outline" className="border-2 border-gray-200 hover:border-blue-300 hover:bg-blue-50 text-lg px-10 py-6 transition-all duration-300">
          Schedule Demo
        </Button>
      </div>
      
      <p className="text-sm text-gray-500 mt-6">
        No credit card required • 30-day free trial • Setup in under 5 minutes
      </p>
    </div>
  </div>
</section>

      {/* Footer */}
      <footer className="bg-gray-900 text-white py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
                <Brain className="w-5 h-5 text-white" />
              </div>
              <span className="text-xl font-semibold">Orris</span>
            </div>
            <div className="text-gray-400 text-sm">
              © 2024 Orris. All rights reserved.
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}
