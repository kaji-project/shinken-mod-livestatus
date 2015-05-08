Name:		shinken-mod-livestatus
Version:	1.4.1
Release:	1kaji0.2
Summary:	Shinken Module Livestatus for Broker

Group:		Network
License:	AGPLv3+
URL:		https://github.com/kaji-project/shinken-mod-livestatus
Source0:	%{name}_%{version}.orig.tar.gz

BuildArch:  noarch

Requires:	shinken-common >= 2.0

%description
Shinken Livestatus module for Broker

%prep
%setup -q


%build


%install
rm -rf %{buildroot}/*

install -d %{buildroot}/usr/share/pyshared/shinken/modules/livestatus
install -pm07555 module/* %{buildroot}/usr/share/pyshared/shinken/modules/livestatus 

install -d %{buildroot}/usr/share/doc/%{name}
install -pm0755 doc/* %{buildroot}/%{_docdir}/%{name}

install -d %{buildroot}/etc/shinken/modules
install -pm0755 etc/modules/* %{buildroot}/etc/shinken/modules


%files
/usr/share/pyshared/shinken/modules/livestatus
%config(noreplace) %{_sysconfdir}/shinken/modules/

%doc %{_docdir}/%{name}/*


%changelog
* Wed Jan 21 2015 Sébastien Coavoux <sebastien.coavoux@savoirfairelinux.com> 1.4.1-1kaji0.2
- Initial Package
