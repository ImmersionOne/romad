class Romad < Formula
  include Language::Python::Virtualenv

  desc "Travel networking toolkit for digital nomads"
  homepage "https://github.com/ImmersionOne/romad"
  url "https://github.com/ImmersionOne/romad/archive/refs/tags/v0.4.0.tar.gz"
  sha256 ""  # Update after creating the release tag
  license "MIT"

  depends_on "python@3.12"

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match "romad", shell_output("#{bin}/romad --version")
  end
end
